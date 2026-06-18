import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import GroundCanvas from '../components/layout/GroundCanvas'
import KnobToggle from '../components/scan/KnobToggle'

// assets
import shovlLogo from '../assets/shovl-logo.svg'
import userAvatarIcon from '../assets/UserAvatar.svg'
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
        <div style={{ 
            position: 'relative', 
            width: '100%', 
            height: '100%', 
            overflow: 'hidden',
            background: '#fff',
            display: 'flex',
            flexDirection: 'column'
        }}>
            
            {/* Navbar */}
            <nav style={{
                display: 'flex', 
                alignItems: 'center',
                justifyContent: 'space-between',
                height: '64px', 
                padding: '0 40px',
                // borderBottom: '2px solid #111111',
                position: 'relative', 
                zIndex: 10, 
                background: 'white',
                width: '100%'
            }}>

                {/* Brand Logo Asset */}
                <div 
                    onClick={() => navigate('/')}
                    role="button"
                    tabIndex={0}
                    aria-label="shovl home"
                    onKeyDown={(e) => e.key === 'Enter' && navigate('/')}
                    style={{ 
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '40px',
                        cursor: 'pointer',
                        userSelect: 'none',
                        outline: 'none',
                        transition: 'transform 0.1s ease'
                    }}
                    onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.97)'}
                    onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
                >
                    <img 
                        src={shovlLogo} 
                        alt="shovl logo" 
                        style={{ 
                            height: '40px', 
                            width: 'auto',
                            pointerEvents: 'none'
                        }} 
                    />
                </div>

                {/* Central URL Input Module */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ 
                        fontFamily: 'var(--font-display)', 
                        fontWeight: 900, 
                        fontSize: '14px' 
                    }}>
                        URL:
                    </span>
                    <input
                        value={url}
                        onChange={e => setUrl(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleScan()}
                        placeholder="paste your API URL..."
                        style={{
                            width: '320px', 
                            height: '38px',
                            // background: '#111111',
                            color: 'var(--color-text)',
                            border: '1px solid var(--color-text)',
                            padding: '0 20px',
                            fontFamily: 'var(--font-mono)', 
                            fontSize: '13px',
                            outline: 'none'
                        }}
                    />
                </div>

                {/* Interactive Account Avatar Action */}
                <div
                    onClick={() => navigate('/signin')}
                    style={{
                        width: '40px', 
                        height: '40px', 
                        borderRadius: '50%',
                        border: '2px solid #111',
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        cursor: 'pointer',
                        overflow: 'hidden',
                        background: '#fff',
                        transition: 'transform 0.1s ease'
                    }}
                    onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.95)'}
                    onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
                >
                    <img 
                        src={userAvatarIcon} 
                        alt="account menu" 
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                    />
                </div>
            </nav>

            {/* Toggles Row - Contained inside a max-width wrapper to prevent edge overflow */}
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
                <KnobToggle
                    label="verbose"
                    active={verbose}
                    onChange={setVerbose}
                    offsetY={0}
                />
                <KnobToggle
                    label="generate report"
                    active={generateReport}
                    onChange={setGenerateReport}
                    offsetY={40}
                />
                <KnobToggle
                    label="suggest fix"
                    active={suggestFix}
                    onChange={setSuggestFix}
                    offsetY={80}
                />
            </div>

            {/* Background Shovel Graphic (Positioned exactly behind the wordmark and emerging from the ground) */}
            <div style={{
                position: 'absolute',
                bottom: '100px', // Sets it directly resting on/penetrating the landscape
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: 1,      // Sits behind the wordmark text (z-index 2) but above the canvas
                pointerEvents: 'none',
                display: 'flex',
                justifyContent: 'center'
            }}>
                <img 
                    src={shovlGraphic} 
                    alt="" 
                    style={{ 
                        height: '480px', // Scales vector proportionally to match reference layout
                        width: 'auto',
                        opacity: 0.85     // Softens blend into background if needed
                    }} 
                />
            </div>

            {/* Wordmark Layout Title Section */}
            <div style={{
                position: 'absolute',
                bottom: '240px',
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
                    color: '#111111'
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
                        fontFamily: 'var(--font-display)', // Uses Arbutus directly
                        fontWeight: 900,
                        fontSize: '16px', // Sweet spot: perfectly readable but less bulky
                        padding: '10px 20px', // Balanced padding
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

            {/* Ground Canvas Engine */}
            <GroundCanvas height={260} />

            {/* Footer Layer */}
            <div style={{
                position: 'absolute', 
                bottom: '10px',
                width: '100%', 
                textAlign: 'center',
                fontFamily: 'var(--font-sans)',
                fontSize: '13px',
                fontWeight: 700,
                // WebkitTextStroke: '.5px var(--color-text)',
                color: 'var(--color-bg)',
                zIndex: 4,
            }}>
                © 2026 Baxigu Dynama. All Rights Reserved
            </div>
        </div>
    )
}