import { useEffect, useRef, useState } from 'react'
import { scanStreamUrl } from '../api/client'

// Consumes the backend SSE endpoint GET /api/scans/stream/.
//
// Why fetch() and not EventSource?
//   The stream endpoint is behind IsAuthenticated, so it needs the JWT in an
//   Authorization header. Native EventSource cannot set headers. fetch() can,
//   and we read the response body as a stream and parse the `data: {...}` lines
//   ourselves.
//
// The backend emits, per check, an object like:
//   { status: 'running', check, progress, total }                 // check started
//   { status: 'result',  check, severity, detail, progress, total } // check finished
// and finally:
//   { status: 'complete', scan_id, risk_score }
//   { status: 'error', check, message }                            // a check blew up
//
// Returns live progress (0..100), a rolling log array, the final scanId, and an
// error string if the connection itself failed.
export default function useScanStream({ targetUrl, verbose = false, suggestFix = false, generateReport = true, enabled = true }) {
    const [progress, setProgress] = useState(0)
    const [logs, setLogs] = useState([
        '>> initializing shovl engine...',
        '>> establishing secure tunnel...',
    ])
    const [scanId, setScanId] = useState(null)
    const [isComplete, setIsComplete] = useState(false)
    const [error, setError] = useState(null)

    // Lets the UI "pause" the visible log without killing the underlying stream.
    const pausedRef = useRef(false)
    const setPaused = (val) => { pausedRef.current = val }

    const abortRef = useRef(null)
    const stop = () => abortRef.current?.abort()

    useEffect(() => {
        if (!enabled || !targetUrl) return

        const controller = new AbortController()
        abortRef.current = controller

        const appendLog = (line) => {
            if (pausedRef.current) return
            setLogs((prev) => {
                const next = [...prev, line]
                return next.length > 14 ? next.slice(next.length - 14) : next
            })
        }

        const handleEvent = (evt) => {
            if (evt.status === 'running') {
                appendLog(`>> [${new Date().toLocaleTimeString()}] running ${evt.check}...`)
                if (evt.total) setProgress(Math.round((evt.progress / evt.total) * 100))
            } else if (evt.status === 'result') {
                const sev = (evt.severity || '').toLowerCase()
                const detail = Array.isArray(evt.detail) ? evt.detail.join('; ') : (evt.detail || '')
                appendLog(`>> ${evt.check} -> [${sev}] ${detail}`)
                if (evt.total) setProgress(Math.round((evt.progress / evt.total) * 100))
            } else if (evt.status === 'error') {
                appendLog(`>> ERROR in ${evt.check}: ${evt.message}`)
            } else if (evt.status === 'complete') {
                setProgress(100)
                setIsComplete(true)
                setScanId(evt.scan_id)
            }
        }

        const run = async () => {
            try {
                const token = localStorage.getItem('access_token')
                const res = await fetch(scanStreamUrl({ target_url: targetUrl, verbose, suggest_fix: suggestFix, generate_report: generateReport }), {
                    method: 'GET',
                    headers: {
                        Authorization: token ? `Bearer ${token}` : '',
                        Accept: 'text/event-stream',
                    },
                    signal: controller.signal,
                })

                if (!res.ok) {
                    setError(`Stream failed (HTTP ${res.status}). Is the domain verified and your session valid?`)
                    return
                }
                if (!res.body) {
                    setError('Stream returned no body — your browser or a proxy may be buffering SSE.')
                    return
                }

                const reader = res.body.getReader()
                const decoder = new TextDecoder()
                let buffer = ''

                // SSE frames are separated by a blank line. Buffer partial chunks
                // and only parse complete "data: ...\n\n" frames.
                // eslint-disable-next-line no-constant-condition
                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break
                    buffer += decoder.decode(value, { stream: true })

                    let sep
                    while ((sep = buffer.indexOf('\n\n')) !== -1) {
                        const frame = buffer.slice(0, sep)
                        buffer = buffer.slice(sep + 2)
                        for (const line of frame.split('\n')) {
                            const trimmed = line.trim()
                            if (!trimmed.startsWith('data:')) continue
                            const payload = trimmed.slice(5).trim()
                            if (!payload) continue
                            try {
                                handleEvent(JSON.parse(payload))
                            } catch {
                                // ignore keep-alive / non-JSON lines
                            }
                        }
                    }
                }
            } catch (err) {
                if (err.name !== 'AbortError') {
                    setError(err.message || 'Scan stream connection failed.')
                }
            }
        }

        run()
        return () => controller.abort()
    }, [targetUrl, verbose, suggestFix, generateReport, enabled])

    return { progress, logs, scanId, isComplete, error, setPaused, stop }
}