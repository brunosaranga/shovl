import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import PageTitle from '../components/common/PageTitle'
import DomainVerificationCard from '../components/domain-verification/DomainVerificationCard'

export default function DomainVerification() {
    const navigate = useNavigate()
    const location = useLocation()

    // Pulls the URL the user typed on the Landing page, defaults if direct navigation
    const targetUrl = location.state?.url || 'api.target-system.com'

    // Simulated verification payload (You will wire this to your backend verification flow)
    const [verificationToken] = useState(() => {
        return `shovl-verify-${Math.random().toString(36).substring(2, 15)}`
    })

    const handleVerified = () => {
        navigate('/scan/running', { state: location.state })
    }

    return (
        <PageShell centerElement={<PageTitle>domain verification</PageTitle>}>
            <DomainVerificationCard
                targetUrl={targetUrl}
                verificationToken={verificationToken}
                onVerified={handleVerified}
            />
        </PageShell>
    )
}