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
            {/* Main layout container wrapper for the verification workspace */}
            <div className="domain-verification-container">
                
                {/* Header section structural wrapper */}
                <div className="verification-header-group">
                    {/* Main brutalist typography title block */}
                    <h1 className="verification-main-title">
                        prove ownership.
                    </h1>
                    {/* Mono-spaced description text displaying target metadata */}
                    <p className="verification-target-desc">
                        target: <strong className="verification-target-badge">{targetUrl}</strong>
                    </p>
                </div>

                {/* Thick-bordered instruction panel block */}
                <div className="dns-instruction-card">
                    {/* Instruction sub-heading text label */}
                    <div className="dns-instruction-step">
                        1. Add this TXT record to your DNS configuration:
                    </div>

                    {/* Dark terminal-styled layout panel displaying the generated token string */}
                    <div className="dns-token-terminal">
                        {/* Token output string container supporting safety text-breaks */}
                        <code className="dns-token-text">
                            {verificationToken}
                        </code>
                        
                        {/* Dynamic utility button providing copy-to-clipboard actions */}
                        <button 
                            onClick={copyToClipboard}
                            style={{
                                background: copied ? 'var(--color-accent)' : '#fff',
                            }}
                            className="dns-copy-button"
                        >
                            {copied ? 'copied!' : 'copy'}
                        </button>
                    </div>

                    {/* Explanatory notice paragraph detailing DNS propagation behavior */}
                    <div className="dns-propagation-note">
                        Note: DNS propagation may take a few minutes. Make sure the record is active before verifying.
                    </div>
                </div>

                {/* Action footer strip containing submission controls */}
                <div className="verification-action-row">
                    {/* Primary multi-state verification confirmation button */}
                    <button
                        onClick={triggerVerification}
                        disabled={status === 'verifying' || status === 'verified'}
                        style={{
                            background: status === 'verified' ? '#4CAF50' : 'var(--color-accent)',
                            cursor: (status === 'verifying' || status === 'verified') ? 'not-allowed' : 'pointer',
                            boxShadow: (status === 'verifying' || status === 'verified') ? '1px 1px 0px var(--color-text)' : '4px 4px 0px var(--color-text)',
                            transform: (status === 'verifying' || status === 'verified') ? 'translate(3px, 3px)' : 'none',
                        }}
                        className="verification-submit-button"
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

                    {/* Structural frame surrounding the stepping loading animation asset */}
                    {status === 'verifying' && (
                        <div className="verification-spinner-wrapper">
                            <style>
                                {`@keyframes spinLogo { 100% { transform: rotate(360deg); } }`}
                            </style>
                            {/* SVG icon node utilizing continuous rotation CSS transforms */}
                            <img src={shovlLogo} alt="verifying" className="verification-spinner-image" />
                        </div>
                    )}
                </div>

            </div>
        </PageShell>
    )
}