import { useState } from 'react'
import shovlLogo from '../../assets/shovl-logo.svg'

// Owns the verify button's state machine and the busy spinner.
// Calls onVerified once the (currently simulated) check succeeds, so the
// parent page can handle navigation.
export default function TriggerVerification({ onVerified, onFailed }) {
    const [status, setStatus] = useState('idle') // 'idle' | 'verifying' | 'verified' | 'failed'

    const handleTrigger = () => {
        setStatus('verifying')

        // Simulate backend DNS lookup delay (wire to real verification later)
        setTimeout(() => {
            const success = true

            if (success) {
                setStatus('verified')
                setTimeout(() => onVerified?.(), 1500)
            } else {
                setStatus('failed')
                onFailed?.()
            }
        }, 2500)
    }

    const handleRetry = () => {
        setStatus('idle')
    }

    const isBusy = status === 'verifying' || status === 'verified'


    const buttonClassName = [
        'verification-submit-button',
        isBusy ? 'is-busy' : '',
        status === 'verified' ? 'is-verified' : '',
        status === 'failed' ? 'is-failed' : '',
    ].filter(Boolean).join(' ')

    return (
        <div className="verification-action-row">
            <button
                onClick={status === 'failed' ? handleRetry : handleTrigger}
                disabled={isBusy}
                className={buttonClassName}
            >
                {status === 'idle' && 'verify ownership'}
                {status === 'verifying' && 'verifying'}
                {status === 'verified' && 'verified.'}
                {status === 'failed' && 'retry'}
            </button>

            {/* Spinner only when actively checking */}
            {status === 'verifying' && (
                <div className="verification-spinner-wrapper">
                    <img src={shovlLogo} alt="verifying" className="verification-spinner-image" />
                </div>
            )}
        </div>
    )
}