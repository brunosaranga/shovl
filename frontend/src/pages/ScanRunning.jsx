import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import ScanHeader from '../components/scan-running/ScanHeader'
import ScanProgressBar from '../components/scan-running/ScanProgressBar'
import ScanTerminal from '../components/scan-running/ScanTerminal'

export default function ScanRunning() {
    const location = useLocation()
    const navigate = useNavigate()
    const targetUrl = location.state?.url || 'api.target-system.com'

    const [scanProgress, setScanProgress] = useState(0)
    const [isPaused, setIsPaused] = useState(false)
    const [logs, setLogs] = useState([
        '>> initializing shovl engine...',
        '>> establishing secure tunnel...',
        '>> analyzing endpoint routing tables...'
    ])

    useEffect(() => {
        if (isPaused) return

        const logInterval = setInterval(() => {
            setLogs(prev => {
                const newLog = `>> [${new Date().toLocaleTimeString()}] probing ${targetUrl} for auth bypass...`
                if (prev.length > 12) return [...prev.slice(1), newLog]
                return [...prev, newLog]
            })
        }, 800)

        const progressInterval = setInterval(() => {
            setScanProgress(prev => {
                if (prev >= 100) {
                    clearInterval(progressInterval)
                    return 100
                }
                return prev + 2
            })
        }, 200)

        return () => {
            clearInterval(logInterval)
            clearInterval(progressInterval)
        }
    }, [targetUrl, isPaused])

    // Redirect to report once scan completes
    useEffect(() => {
        if (scanProgress === 100) {
            const timer = setTimeout(() => navigate('/report', { state: location.state }), 2000)
            return () => clearTimeout(timer)
        }
    }, [scanProgress, navigate, location.state])

    return (
        <PageShell title="scan running">
            <div className="scan-running-container">
                <ScanHeader
                    targetUrl={targetUrl}
                    isPaused={isPaused}
                    onTogglePause={() => setIsPaused(p => !p)}
                    onStop={() => console.log('Scan manually stopped by user.')}
                />
                <ScanProgressBar progress={scanProgress} />
                <ScanTerminal logs={logs} isComplete={scanProgress === 100} />
            </div>
        </PageShell>
    )
}