import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import PageTitle from '../components/common/PageTitle'
import DomainVerificationCard from '../components/domain-verification/DomainVerificationCard'
import { domainsAPI } from '../api/client'
import { extractHostname, isPracticeTarget } from '../api/targets'

export default function DomainVerification() {
    const navigate = useNavigate()
    const location = useLocation()

    const targetUrl = location.state?.url || ''
    const hostname = extractHostname(targetUrl)

    const [domainId, setDomainId] = useState(null)
    const [verificationToken, setVerificationToken] = useState(null)
    const [loading, setLoading] = useState(true)
    const [loadError, setLoadError] = useState(null)

    // Practice targets (httpbin, postman-echo, localhost, 127.0.0.1) need no proof
    // of ownership — go straight to the scan.
    useEffect(() => {
        if (!targetUrl) {
            navigate('/', { replace: true })
            return
        }
        if (isPracticeTarget(targetUrl)) {
            navigate('/scan/running', { state: location.state, replace: true })
        }
    }, [targetUrl, location.state, navigate])

    // Ensure a Domain record exists for this hostname and grab its REAL token.
    // The token is generated server-side (secrets.token_hex), so we never fabricate it.
    useEffect(() => {
        if (!hostname || isPracticeTarget(targetUrl)) return

        let cancelled = false

        const ensureDomain = async () => {
            setLoading(true)
            setLoadError(null)
            try {
                // Try to create it. unique_together(user, hostname) means a repeat
                // returns 400 — in that case we look it up in the list instead.
                let domain
                try {
                    const res = await domainsAPI.add({ hostname })
                    domain = res.data
                } catch (err) {
                    if (err.response?.status === 400) {
                        const list = await domainsAPI.list()
                        domain = list.data.find((d) => d.hostname === hostname)
                    } else {
                        throw err
                    }
                }

                if (!domain) throw new Error('Could not create or find this domain.')
                if (cancelled) return

                setDomainId(domain.id)
                setVerificationToken(domain.verification_token)

                // Already verified from a previous run? Skip ahead.
                if (domain.verified) {
                    navigate('/scan/running', { state: location.state, replace: true })
                }
            } catch (err) {
                if (!cancelled) {
                    setLoadError(
                        err.response?.data?.detail ||
                        err.message ||
                        'Failed to set up domain verification.'
                    )
                }
            } finally {
                if (!cancelled) setLoading(false)
            }
        }

        ensureDomain()
        return () => { cancelled = true }
    }, [hostname, targetUrl, location.state, navigate])

    const handleVerified = () => {
        navigate('/scan/running', { state: location.state })
    }

    return (
        <PageShell centerElement={<PageTitle>domain verification</PageTitle>}>
            {loading && (
                <div className="domain-verification-container">
                    <p className="verification-target-desc">setting up verification for {hostname}...</p>
                </div>
            )}

            {!loading && loadError && (
                <div className="domain-verification-container">
                    <div className="verification-failed-panel">
                        <span className="verification-failed-label">setup failed.</span>
                        <ul className="verification-failed-reasons">
                            <li>{loadError}</li>
                        </ul>
                    </div>
                </div>
            )}

            {!loading && !loadError && domainId && (
                <DomainVerificationCard
                    hostname={hostname}
                    targetUrl={targetUrl}
                    domainId={domainId}
                    verificationToken={verificationToken}
                    onVerified={handleVerified}
                />
            )}
        </PageShell>
    )
}