import { PrimaryButton } from '../layout/Buttons'
import getRiskHeadline from '../common/riskHeadline'

// Top summary strip — target, runtime, risk score, re-run action.
// Driven by the real report.meta. The risk score is rendered as a colored badge
// per the scan-outcome truth table (see common/riskHeadline.js), including the
// neutral INCOMPLETE state and a coverage caption when checks errored.
export default function ReportMetaCard({ meta, summary = {}, targetUrl, onReRun }) {
    const target = meta?.target || targetUrl || '—'
    const scannedAt = meta?.scanned_at
        ? new Date(meta.scanned_at).toLocaleString()
        : '—'
    const risk = (meta?.risk_score || '').toUpperCase()
    const headline = getRiskHeadline(meta?.risk_score)

    // Coverage: how many checks actually ran vs errored out. ERROR means a check
    // failed to run, not that the target is clean — so we surface it explicitly.
    const total = meta?.total_checks
        ?? Object.values(summary).reduce((sum, n) => sum + (n || 0), 0)
    const errors = summary?.ERROR || 0
    const completed = Math.max(total - errors, 0)

    let caption = null
    if (risk === 'INCOMPLETE') {
        caption = `0 of ${total} checks completed — Shovl couldn't assess this target. Re-run the scan.`
    } else if (errors > 0) {
        caption = `${completed} of ${total} checks completed — ${errors} errored, so coverage is partial.`
    }

    return (
        <div className="report-meta-card">
            <div className="report-meta-details">
                <div className="report-meta-line">
                    <span className="report-meta-label">target: </span>
                    <span>{target}</span>
                </div>
                <div className="report-meta-line">
                    <span className="report-meta-label">runtime: </span>
                    <span>{scannedAt}</span>
                </div>
                <div className="report-meta-line report-meta-risk-line">
                    <span className="report-meta-label">risk score: </span>
                    <span
                        className="report-meta-risk-badge"
                        style={{ background: headline.bg, color: headline.fg }}
                    >
                        {headline.label}
                    </span>
                </div>
                {caption && <div className="report-meta-caption">{caption}</div>}
            </div>
            <PrimaryButton onClick={onReRun}>re-run scan</PrimaryButton>
        </div>
    )
}