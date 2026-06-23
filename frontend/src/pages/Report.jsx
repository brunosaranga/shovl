import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import PageTitle from '../components/common/PageTitle'
import ReportMetaCard from '../components/report/ReportMetaCard'
import SeverityMatrix from '../components/report/SeverityMatrix'
import FindingsList from '../components/report/FindingsList'
import { scansAPI } from '../api/client'

export default function Report() {
    const { scanId } = useParams()
    const navigate = useNavigate()

    const [scan, setScan] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [openFindingId, setOpenFindingId] = useState(null)

    useEffect(() => {
        let cancelled = false
        const load = async () => {
            setLoading(true)
            setError(null)
            try {
                const res = await scansAPI.detail(scanId)
                if (!cancelled) setScan(res.data)
            } catch (err) {
                if (!cancelled) {
                    setError(
                        err.response?.status === 404
                            ? 'Report not found.'
                            : (err.response?.data?.error || 'Failed to load report.')
                    )
                }
            } finally {
                if (!cancelled) setLoading(false)
            }
        }
        load()
        return () => { cancelled = true }
    }, [scanId])

    const report = scan?.results || null

    return (
        <PageShell centerElement={<PageTitle>report</PageTitle>}>
            <div className="report-container">
                {loading && <p className="report-meta-line">loading report...</p>}

                {!loading && error && (
                    <div className="verification-failed-panel">
                        <span className="verification-failed-label">{error}</span>
                    </div>
                )}

                {!loading && !error && report && (
                    <>
                        <ReportMetaCard
                            meta={report.meta}
                            targetUrl={scan.target_url}
                            onReRun={() =>
                                navigate('/scan/running', {
                                    state: {
                                        url: scan.target_url,
                                        verbose: scan.verbose,
                                        suggest_fix: scan.suggest_fix,
                                    },
                                })
                            }
                        />
                        <SeverityMatrix summary={report.summary} riskScore={report.meta?.risk_score} />
                        <FindingsList
                            findings={report.findings || []}
                            suggestFix={report.meta?.suggest_fix}
                            openFindingId={openFindingId}
                            setOpenFindingId={setOpenFindingId}
                        />
                    </>
                )}
            </div>
        </PageShell>
    )
}