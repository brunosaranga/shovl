import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import PageTitle from '../components/common/PageTitle'

import shovlLogo from '../assets/shovl-logo.svg'

export default function DomainVerification() {
    const navigate = useNavigate()
    const location = useLocation()
    
    // Pulls the URL the user typed on the Landing page, defaults if direct navigation
    const targetUrl = location.state?.url || 'api.target-system.com'
    
    const [status, setStatus] = useState('idle') // 'idle' | 'verifying' | 'verified' | 'failed'
    const [copied, setCopied] = useState(false)

    // Simulated verification payload (You will wire this to your backend verification flow)
    const [verificationToken] = useState(() => {
        return `shovl-verify-${Math.random().toString(36).substring(2, 15)}`
    })
    const copyToClipboard = () => {
        navigator.clipboard.writeText(verificationToken)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const triggerVerification = () => {
        setStatus('verifying')
        
        // Simulate backend DNS lookup delay
        setTimeout(() => {
            // Fake success state for frontend testing
            setStatus('verified')
            // Auto-route to the active scan screen after success
            setTimeout(() => navigate('/scan/running', { state: location.state }), 1500)
        }, 2500)
    }

    return (
        <PageShell centerElement={<PageTitle>domain verification</PageTitle>}>
            <div style={{
                maxWidth: '800px',
                margin: '0 auto',
                paddingTop: '40px',
                display: 'flex',
                flexDirection: 'column',
                gap: '40px'
            }}>
                
                {/* Header Section */}
                <div>
                    <h1 style={{
                        fontFamily: 'var(--font-display)',
                        fontSize: '48px',
                        fontWeight: 900,
                        letterSpacing: '-2px',
                        color: 'var(--color-text)',
                        margin: '0 0 16px 0',
                        lineHeight: 1.1
                    }}>
                        prove ownership.
                    </h1>
                    <p style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '15px',
                        color: 'var(--color-text)',
                        margin: 0,
                        opacity: 0.8
                    }}>
                        target: <strong style={{ color: 'var(--color-accent)', background: '#111', padding: '2px 8px' }}>{targetUrl}</strong>
                    </p>
                </div>

                {/* Instruction Card */}
                <div style={{
                    border: '4px solid var(--color-text)',
                    background: '#fff',
                    boxShadow: '8px 8px 0px var(--color-text)',
                    padding: '40px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '24px'
                }}>
                    <div style={{ fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600 }}>
                        1. Add this TXT record to your DNS configuration:
                    </div>

                    {/* Terminal Block */}
                    <div style={{
                        background: 'var(--color-text)',
                        color: '#fff',
                        padding: '20px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '20px'
                    }}>
                        <code style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '14px',
                            wordBreak: 'break-all'
                        }}>
                            {verificationToken}
                        </code>
                        
                        <button 
                            onClick={copyToClipboard}
                            style={{
                                background: copied ? 'var(--color-accent)' : '#fff',
                                color: 'var(--color-text)',
                                border: 'none',
                                padding: '8px 16px',
                                fontFamily: 'var(--font-mono)',
                                fontWeight: 800,
                                fontSize: '12px',
                                cursor: 'pointer',
                                transition: 'all 0.1s ease',
                                flexShrink: 0
                            }}
                        >
                            {copied ? 'copied!' : 'copy'}
                        </button>
                    </div>

                    <div style={{ fontFamily: 'var(--font-sans)', fontSize: '14px', color: 'var(--color-muted)', }}>
                        Note: DNS propagation may take a few minutes. Make sure the record is active before verifying.
                    </div>
                </div>

                {/* Action Section */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginTop: '20px' }}>
                    <button
                        onClick={triggerVerification}
                        disabled={status === 'verifying' || status === 'verified'}
                        style={{
                            background: status === 'verified' ? '#4CAF50' : 'var(--color-accent)',
                            color: 'var(--color-text)',
                            fontFamily: 'var(--font-display)',
                            fontWeight: 900,
                            fontSize: '16px',
                            padding: '10px 20px',
                            border: '2px solid var(--color-text)',
                            cursor: (status === 'verifying' || status === 'verified') ? 'not-allowed' : 'pointer',
                            boxShadow: (status === 'verifying' || status === 'verified') ? '1px 1px 0px var(--color-text)' : '4px 4px 0px var(--color-text)',
                            transform: (status === 'verifying' || status === 'verified') ? 'translate(3px, 3px)' : 'none',
                            transition: 'all 0.1s ease',
                            textTransform: 'lowercase'
                        }}
                        onMouseDown={(e) => {
                            if (status !== 'idle') return
                            e.currentTarget.style.transform = 'translate(3px, 3px)'
                            e.currentTarget.style.boxShadow = '1px 1px 0px var(--color-text)'
                        }}
                        onMouseUp={(e) => {
                            if (status !== 'idle') return
                            e.currentTarget.style.transform = 'translate(0px, 0px)'
                            e.currentTarget.style.boxShadow = '4px 4px 0px var(--color-text)'
                        }}
                    >
                        {status === 'idle' && 'verify ownership'}
                        {status === 'verifying' && 'verifying'}
                        {status === 'verified' && 'verified.'}
                    </button>

                    {/* Simple loading spinner/indicator */}
                    {status === 'verifying' && (
                        <div style={{
                            width: '24px',
                            // height: '24px',
                            // border: '4px solid #eee',
                            // borderTopColor: 'var(--color-text)',
                            // borderRadius: '50%',
                            // animation: 'spin 1s linear infinite'
                        }}>
                            <style>
                                {`@keyframes spinLogo { 100% { transform: rotate(360deg); } }`}
                            </style>
                            <img src={shovlLogo} alt="verifying" style={{
                                width: '100%',
                                height: '100%',
                                animation: 'spinLogo .8s steps(8, end)  infinite'
                            }} />
                        </div>
                    )}
                </div>

            </div>
        </PageShell>
    )
}