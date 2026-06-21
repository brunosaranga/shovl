import CopyToClipboard from './CopyToClipboard'
import TriggerVerification from './TriggerVerification'

export default function DomainVerificationCard({ targetUrl, verificationToken, onVerified }) {
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

                <CopyToClipboard token={verificationToken} />

                <div className="dns-propagation-note">
                    Note: DNS propagation may take a few minutes. Make sure the record is active before verifying.
                </div>
            </div>

            <TriggerVerification onVerified={onVerified} />

        </div>
    )
}