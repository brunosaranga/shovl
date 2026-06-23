import { useState } from 'react'
import CopyToClipboard from './CopyToClipboard'
import TriggerVerification from './TriggerVerification'

export default function DomainVerificationCard({
    hostname,
    targetUrl,
    domainId,
    verificationToken,
    onVerified,
}) {
    const [failed, setFailed] = useState(false)

    // The exact TXT record the backend checks for (domains/verification.py):
    //   host:  _shovl-verify.<hostname>
    //   value: <verification_token>
    const recordName = `_shovl-verify.${hostname}`

    return (
        <div className="domain-verification-container">

            {/* Header section structural wrapper */}
            <div className="verification-header-group">
                <h1 className="verification-main-title">
                    prove ownership.
                </h1>
                <p className="verification-target-desc">
                    target: <strong className="verification-target-badge">{targetUrl}</strong>
                </p>
            </div>

            {/* Thick-bordered instruction panel block */}
            <div className="dns-instruction-card">
                <div className="dns-instruction-step">
                    1. Add this TXT record to your DNS configuration:
                </div>

                <div className="dns-record-row">
                    <span className="dns-record-label">host / name:</span>
                    <code className="dns-record-value">{recordName}</code>
                </div>

                <div className="dns-record-row">
                    <span className="dns-record-label">type:</span>
                    <code className="dns-record-value">TXT</code>
                </div>

                <div className="dns-record-row">
                    <span className="dns-record-label">value:</span>
                    <CopyToClipboard token={verificationToken} />
                </div>

                <div className="dns-propagation-note">
                    Note: DNS propagation may take a few minutes. Make sure the record is active before verifying.
                </div>
            </div>

            {/* Failed state panel - rendered only after a failed attempt */}
            {failed && (
                <div className='verification-failed-panel'>
                    <span className='verification-failed-label'>verification failed.</span>
                    <ul className='verification-failed-reasons'>
                        <li>DNS propagation can take up to 24 hours — wait a few minutes and retry.</li>
                        <li>Make sure the record type is <strong>TXT</strong>, not CNAME or A.</li>
                        <li>Make sure the host is exactly <strong>{recordName}</strong>.</li>
                        <li>Check for typos in the value — copy it again using the button above.</li>
                    </ul>
                </div>
            )}

            <TriggerVerification
                domainId={domainId}
                onVerified={onVerified}
                onFailed={() => setFailed(true)}
            />

        </div>
    )
}