import { useState } from 'react'
import shovlLogo from '../../assets/shovl-logo.svg'

// Owns the verify button's state machine and the busy spinner.
// Calls onVerified once the (currently simulated) check succeeds, so the
// parent page can handle navigation.
export default function TriggerVerification({ onVerified }) {
    const [status, setStatus] = useState('idle') // 'idle' | 'verifying' | 'verified' | 'failed'

    const handleTrigger = () => {
        setStatus('verifying')

        // Simulate backend DNS lookup delay (wire to real verification later)
        setTimeout(() => {
            setStatus('verified')
            setTimeout(() => {
                onVerified?.()
            }, 1500)
        }, 2500)
    }

    const isBusy = status === 'verifying' || status === 'verified'

    const buttonClassName = [
        'verification-submit-button',
        isBusy ? 'is-busy' : '',
        status === 'verified' ? 'is-verified' : '',
    ].filter(Boolean).join(' ')

    return (
        <div className="verification-action-row">
            <button
                onClick={handleTrigger}
                disabled={isBusy}
                className={buttonClassName}
            >
                {status === 'idle' && 'verify ownership'}
                {status === 'verifying' && 'verifying'}
                {status === 'verified' && 'verified.'}
            </button>

            {status === 'verifying' && (
                <div className="verification-spinner-wrapper">
                    <img src={shovlLogo} alt="verifying" className="verification-spinner-image" />
                </div>
            )}
        </div>
    )
}