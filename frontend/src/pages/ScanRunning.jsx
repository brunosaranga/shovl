import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import shovlLogo from '../assets/shovl-logo.svg'

export default function ScanRunning() {
    const location = useLocation()
    const targetUrl = location.state?.url || 'api.target-system.com'
    
    const [scanProgress, setScanProgress] = useState(0)
    const [isPaused, setIsPaused] = useState(false)
    const [logs, setLogs] = useState([
        '>> initializing shovl engine...',
        '>> establishing secure tunnel...',
        '>> analyzing endpoint routing tables...'
    ])
    
    // Simulated log stream representing offensive security checks
    useEffect(() => {
        if (isPaused) return // Pauses intervals when toggled

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

    // Common button square styling matching the 50x50 animated logo box
    const squareActionStyle = {
        width: '43px',
        height: '43px',
        background: '#fff',
        border: '2px solid var(--color-text)',
        cursor: 'pointer',
        boxShadow: '4px 4px 0px var(--color-text)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        // transition: 'all 0.1s ease',
        textTransform: 'lowercase'
    }

    const handleMouseDown = (e) => {
        e.currentTarget.style.transform = 'translate(2px, 2px)'
        e.currentTarget.style.boxShadow = '1px 1px 0px var(--color-text)'
    }

    const handleMouseUp = (e) => {
        e.currentTarget.style.transform = 'translate(0px, 0px)'
        e.currentTarget.style.boxShadow = '4px 4px 0px var(--color-text)'
    }

    return (
        <PageShell title="scan running">
            <div style={{
                maxWidth: '960px',
                margin: '0 auto',
                paddingTop: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '32px'
            }}>
                
                {/* Status Header: Title, Control Buttons + Animated Shovel */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 style={{
                            fontFamily: 'var(--font-display)',
                            fontSize: '34px',
                            fontWeight: 900,
                            letterSpacing: '-2px',
                            color: 'var(--color-text)',
                            margin: '0 0 8px 0',
                            lineHeight: 1
                        }}>
                            digging deeper...
                        </h1>
                        <p style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '14px',
                            color: 'var(--color-muted)',
                            margin: 0
                        }}>
                            Targeting: {targetUrl}
                        </p>
                    </div>

                    {/* Controls & Status Group */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        
                        {/* Pause/Play Toggle Button (Boxed Square) */}
                        <button
                            onClick={() => setIsPaused(!isPaused)}
                            style={squareActionStyle}
                            onMouseDown={handleMouseDown}
                            onMouseUp={handleMouseUp}
                        >
                            <span style={{ 
                                fontFamily: 'var(--font-sans)', 
                                fontWeight: 900, 
                                fontSize: '16px',
                                color: 'var(--color-text)' 
                            }}>
                                {isPaused ? '▶' : '||'}
                            </span>
                        </button>

                        {/* Stop Button (Vintage Red Boxed Square) */}
                        <button
                            onClick={() => console.log('Scan manually stopped by user.')}
                            style={{
                                ...squareActionStyle,
                                background: '#ff4d4f',
                                width: '43px', 
                                height: '43px', // Vintage/Alert Red
                            }}
                            onMouseDown={handleMouseDown}
                            onMouseUp={handleMouseUp}
                        >
                            <span style={{ 
                                width: '14px', 
                                height: '14px', 
                                background: 'var(--color-text)',
                                display: 'inline-block' 
                            }} />
                        </button>

                        {/* Spinning Logo Container */}
                        <div style={{
                            width: '43px',
                            height: '43px',
                            border: '2px solid var(--color-text)',
                            background: '#fff',
                            boxShadow: '4px 4px 0px var(--color-text)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <style>
                                {`@keyframes spinLogo { 100% { transform: rotate(360deg); } }`}
                            </style>
                            <img 
                                src={shovlLogo} 
                                alt="scan active" 
                                style={{ 
                                    height: '25px', 
                                    width: '25px', 
                                    animation: isPaused 
                                        ? 'none' 
                                        : 'spinLogo .8s steps(8, end) infinite' 
                                }}
                            />
                        </div>
                    </div>
                </div>

                {/* Progress Bar Track */}
                <div style={{
                    width: '100%',
                    height: '16px',
                    border: '3px solid var(--color-text)',
                    background: '#fff',
                    padding: '2px',
                    boxShadow: '4px 4px 0px var(--color-text)'
                }}>
                    <div style={{
                        height: '100%',
                        background: 'var(--color-accent)',
                        width: `${scanProgress}%`,
                        transition: 'width 1s steps(8, end)'
                    }} />
                </div>

                {/* Terminal Stream Output */}
                <div style={{
                    background: 'var(--color-text)',
                    color: '#fff',
                    border: '4px solid var(--color-text)',
                    boxShadow: '8px 8px 0px rgb(183, 86, 46, 0.5)',
                    padding: '24px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '13px',
                    lineHeight: 1.6,
                    height: '320px',
                    overflowY: 'hidden',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                }}>
                    {logs.map((log, index) => (
                        <div key={index} style={{
                            opacity: index === logs.length - 1 ? 1 : 0.7
                        }}>
                            {log}
                        </div>
                    ))}
                    {scanProgress === 100 && (
                        <div style={{ color: '#4CAF50', marginTop: '12px' }}>
                            {">> scan complete! redirecting to vulnerability results..."}
                        </div>
                    )}
                </div>

            </div>
        </PageShell>
    )
}