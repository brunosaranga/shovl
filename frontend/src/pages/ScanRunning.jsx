import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import ScanHeader from '../components/scan-running/ScanHeader'
import ScanProgressBar from '../components/scan-running/ScanProgressBar'
import ScanTerminal from '../components/scan-running/ScanTerminal'
import useScanStream from '../hooks/useScanStream'

// Drives the live scan via the backend SSE stream. No scanId in the route here —
// the backend only mints the Scan record (and its id) once every check is done,
// so we receive it in the final 'complete' event and navigate to the report then.
export default function ScanRunning() {
    const location = useLocation()
    const navigate = useNavigate()

    const targetUrl = location.state?.url
    const verbose = location.state?.verbose ?? false
    const suggestFix = location.state?.suggest_fix ?? false

    const [isPaused, setIsPaused] = useState(false)

    const { progress, logs, scanId, isComplete, error, setPaused, stop } = useScanStream({
        targetUrl,
        verbose,
        suggestFix,
        enabled: Boolean(targetUrl),
    })

    // If someone lands here without a target (e.g. refresh, deep link), bounce home.
    useEffect(() => {
        if (!targetUrl) navigate('/', { replace: true })
    }, [targetUrl, navigate])

    // Once the stream reports completion with a real scan id, go to the report.
    useEffect(() => {
        if (isComplete && scanId) {
            const timer = setTimeout(
                () => navigate(`/scan/${scanId}/report`, { state: { url: targetUrl } }),
                1500
            )
            return () => clearTimeout(timer)
        }
    }, [isComplete, scanId, navigate, targetUrl])

    const handleTogglePause = () => {
        setIsPaused((p) => {
            const next = !p
            setPaused(next) // freezes the visible log; the stream keeps running underneath
            return next
        })
    }

    const handleStop = () => {
        stop()
        navigate('/dashboard')
    }

    return (
        <PageShell title="scan running">
            <div className="scan-running-container">
                <ScanHeader
                    targetUrl={targetUrl}
                    isPaused={isPaused}
                    onTogglePause={handleTogglePause}
                    onStop={handleStop}
                />
                <ScanProgressBar progress={progress} />
                <ScanTerminal
                    logs={error ? [...logs, `>> ${error}`] : logs}
                    isComplete={isComplete}
                />
            </div>
        </PageShell>
    )
}