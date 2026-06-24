import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import PageTitle from '../components/common/PageTitle'
import ReportMetaCard from '../components/report/ReportMetaCard'
import SeverityMatrix from '../components/report/SeverityMatrix'
import FindingsList, { findingKey } from '../components/report/FindingsList'
import { scansAPI } from '../api/client'

export default function Report() {
    const { scanId } = useParams()
    const navigate = useNavigate()

    const [scan, setScan] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [openIds, setOpenIds] = useState(() => new Set())

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
    // generate_report off => summary only (meta + severity matrix), no findings breakdown.
    const showFindings = report?.meta?.generate_report !== false

    useEffect(() => {
        const findings = scan?.results?.findings
        if (!findings) return
        const initial = new Set()
        findings.forEach((f, i) => {
            if ((f.severity || '').toUpperCase() !== 'PASS') initial.add(findingKey(f, i))
        })
        setOpenIds(initial)
    }, [scan])

    const toggleFinding = (key) =>
        setOpenIds((prev) => {
            const next = new Set(prev)
            next.has(key) ? next.delete(key) : next.add(key)
            return next
        })
    const expandAll = (keys) => setOpenIds(new Set(keys))
    const collapseAll = () => setOpenIds(new Set())

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
                                        generate_report: report.meta?.generate_report ?? true,
                                    },
                                })
                            }
                        />
                        <SeverityMatrix summary={report.summary} riskScore={report.meta?.risk_score} />

                        {showFindings ? (
                            <FindingsList
                                findings={report.findings || []}
                                suggestFix={report.meta?.suggest_fix}
                                openIds={openIds}
                                onToggle={toggleFinding}
                                onExpandAll={expandAll}
                                onCollapseAll={collapseAll}
                            />
                        ) : (
                            <div className="report-summary-note">
                                <p className="report-meta-line">
                                    summary only — the full findings breakdown was skipped because
                                    "generate report" was off for this scan.
                                </p>
                                <button
                                    type="button"
                                    className="findings-control-btn"
                                    onClick={() =>
                                        navigate('/scan/running', {
                                            state: {
                                                url: scan.target_url,
                                                verbose: scan.verbose,
                                                suggest_fix: scan.suggest_fix,
                                                generate_report: true,
                                            },
                                        })
                                    }
                                >
                                    re-run with full report
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>
        </PageShell>
    )
}