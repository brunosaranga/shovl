import { useState } from 'react'
import shovlLogo from '../../assets/shovl-logo.svg'
import { domainsAPI } from '../../api/client'

// Owns the verify button's state machine + spinner, and now makes the REAL call:
//   POST /api/domains/<id>/verify/  ->  { status: 'verified' }            (success)
//                                       { status: 'failed', detail }      (no record yet)
// On success it calls onVerified so the parent page can navigate to the scan.
export default function TriggerVerification({ domainId, onVerified, onFailed }) {
    const [status, setStatus] = useState('idle') // 'idle' | 'verifying' | 'verified' | 'failed'

    const handleTrigger = async () => {
        setStatus('verifying')
        try {
            const res = await domainsAPI.verify(domainId)
            if (res.data?.status === 'verified') {
                setStatus('verified')
                setTimeout(() => onVerified?.(), 1200)
            } else {
                setStatus('failed')
                onFailed?.()
            }
        } catch {
            // Backend returns 400 when the TXT record isn't found yet.
            setStatus('failed')
            onFailed?.()
        }
    }

    const handleRetry = () => setStatus('idle')

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

            {status === 'verifying' && (
                <div className="verification-spinner-wrapper">
                    <img src={shovlLogo} alt="verifying" className="verification-spinner-image" />
                </div>
            )}
        </div>
    )
}