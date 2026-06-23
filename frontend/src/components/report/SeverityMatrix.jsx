// Severity distribution row, driven by the real report.summary counts.
// Backend severities are HIGH / MEDIUM / LOW / PASS / ERROR (uppercase). There is
// no per-finding "critical" — CRITICAL only exists as the aggregate risk score,
// which we surface separately in the meta card.
const TIERS = [
    { key: 'HIGH',   label: 'High',   color: 'var(--color-errors)' },
    { key: 'MEDIUM', label: 'Medium', color: 'var(--color-sev-high)' },
    { key: 'LOW',    label: 'Low',    color: 'var(--color-sev-medium)' },
    { key: 'PASS',   label: 'Passed', color: 'var(--color-sev-low)' },
    { key: 'ERROR',  label: 'Errors', color: 'var(--color-sev-low)' },
]

export default function SeverityMatrix({ summary = {} }) {
    return (
        <div className="severity-matrix-grid">
            {TIERS.map((tier) => (
                <div key={tier.key} className="severity-matrix-box">
                    <div className="severity-matrix-header" style={{ background: tier.color }}>
                        {tier.label}
                    </div>
                    <div className="severity-matrix-count">{summary[tier.key] ?? 0}</div>
                </div>
            ))}
        </div>
    )
}