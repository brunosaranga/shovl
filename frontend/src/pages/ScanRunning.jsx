import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import ScanHeader from '../components/scan-running/ScanHeader'
import ScanProgressBar from '../components/scan-running/ScanProgressBar'
import ScanTerminal from '../components/scan-running/ScanTerminal'
import useScanStream from '../hooks/useScanStream'

export default function ScanRunning() {
    const location = useLocation()
    const navigate = useNavigate()

    const targetUrl = location.state?.url
    const verbose = location.state?.verbose ?? false
    const suggestFix = location.state?.suggest_fix ?? false
    const generateReport = location.state?.generate_report ?? true

    const [isPaused, setIsPaused] = useState(false)

    const { progress, logs, scanId, isComplete, error, setPaused, stop } = useScanStream({
        targetUrl,
        verbose,
        suggestFix,
        generateReport,
        enabled: Boolean(targetUrl),
    })

    useEffect(() => {
        if (!targetUrl) navigate('/', { replace: true })
    }, [targetUrl, navigate])

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
            setPaused(next)
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

                {/* Verbose is the live-output knob: only stream the terminal when it's on. */}
                {verbose ? (
                    <ScanTerminal
                        logs={error ? [...logs, `>> ${error}`] : logs}
                        isComplete={isComplete}
                    />
                ) : (
                    error && <p className="report-meta-line">{`>> ${error}`}</p>
                )}
            </div>
        </PageShell>
    )
}