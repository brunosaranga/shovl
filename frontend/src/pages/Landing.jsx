import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

import KnobToggle from '../components/scan/KnobToggle'
import PageShell from '../components/layout/PageShell'

import shovlGraphic from '../assets/ShovelGraphic.svg'

export default function Landing() {
    const [url, setUrl] = useState('')
    const [verbose, setVerbose ] = useState(false)
    const [generateReport, setGenerateReport] = useState(true)
    const [suggestFix, setSuggestFix] = useState(false)
    const { accessToken } = useAuth()
    const navigate = useNavigate()

    const handleScan = () => {
        if (!accessToken) {
            navigate('/signin', { state: { pendingScan: { url, verbose, generateReport, suggestFix } } })
            return
        }
        navigate('/scan/new', { state: { url, verbose, generateReport, suggestFix} })
    }

    return (
        <PageShell title="landing" isLanding={true}>
            <div style={{ 
                position: 'absolute', 
                inset: 0, // Pins this container to top:0, left:0, right:0, bottom:0
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
            }}>
                
                {/* Toggles Row */}
                <div style={{
                    width: '100%',
                    top: '10px',
                    maxWidth: '900px',
                    margin: '0 auto',
                    display: 'flex', 
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    padding: '60px 0 0',
                    position: 'relative',
                    zIndex: 5,
                }}>
                    <KnobToggle label="verbose" active={verbose} onChange={setVerbose} offsetY={0} />
                    <KnobToggle label="generate report" active={generateReport} onChange={setGenerateReport} offsetY={40} />
                    <KnobToggle label="suggest fix" active={suggestFix} onChange={setSuggestFix} offsetY={80} />
                </div>

                {/* Background Shovel Graphic */}
                <div style={{
                    position: 'absolute',
                    bottom: '100px', 
                    left: '50%',
                    transform: 'translateX(-50%)',
                    zIndex: 1,      
                    pointerEvents: 'none',
                    display: 'flex',
                    justifyContent: 'center'
                }}>
                    <img src={shovlGraphic} alt="" style={{ height: '480px', width: 'auto', opacity: 0.85 }} />
                </div>

                {/* Wordmark Layout Title Section */}
                <div style={{
                    position: 'absolute',
                    bottom: '220px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    textAlign: 'center',
                    zIndex: 2,
                }}>
                    <h1 style={{
                        fontFamily: 'var(--font-display)',
                        fontSize: '120px',
                        fontWeight: 900,
                        lineHeight: 1,
                        letterSpacing: '-6px',
                        userSelect: 'none',
                        color: 'var(--color-text)'
                    }}>
                        shovl
                    </h1>
                </div>

                {/* Primary Action Button */}
                <div style={{
                    position: 'absolute',
                    bottom: '80px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    zIndex: 3,
                }}>
                    <button
                        onClick={handleScan}
                        style={{
                            background: 'var(--color-accent)', 
                            color: 'var(--color-text)',
                            fontFamily: 'var(--font-display)', 
                            fontWeight: 900,
                            fontSize: '16px', 
                            padding: '10px 20px', 
                            border: '2px solid #111',
                            borderRadius: '0px', 
                            cursor: 'pointer',
                            boxShadow: '4px 4px 0px var(--color-text)', 
                            transition: 'all 0.1s ease',
                            textTransform: 'lowercase'
                        }}
                        onMouseDown={(e) => {
                            e.currentTarget.style.transform = 'translate(2px, 2px)'
                            e.currentTarget.style.boxShadow = '1px 1px 0px #111'
                        }}
                        onMouseUp={(e) => {
                            e.currentTarget.style.transform = 'translate(0px, 0px)'
                            e.currentTarget.style.boxShadow = '3px 3px 0px #111'
                        }}
                    >
                        dig deeper
                    </button>
                </div>
            </div>
        </PageShell>
    )
}