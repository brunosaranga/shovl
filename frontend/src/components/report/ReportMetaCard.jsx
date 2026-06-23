import { PrimaryButton } from '../layout/Buttons'

// Top summary strip — target, runtime, risk score, re-run action.
// Driven by the real report.meta now.
export default function ReportMetaCard({ meta, targetUrl, onReRun }) {
    const target = meta?.target || targetUrl || '—'
    const scannedAt = meta?.scanned_at
        ? new Date(meta.scanned_at).toLocaleString()
        : '—'
    const risk = meta?.risk_score || '—'

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
                <div className="report-meta-line">
                    <span className="report-meta-label">risk score: </span>
                    <span>{risk}</span>
                </div>
            </div>
            <PrimaryButton onClick={onReRun}>re-run scan</PrimaryButton>
        </div>
    )
}