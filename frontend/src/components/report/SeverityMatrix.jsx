// Severity distribution row. Local mock data for now — wire to real scan
// results once the backend exists.
const severityTiers = [
    { id: 'critical', label: 'Critical', color: 'var(--color-text)', count: 1 },
    { id: 'high', label: 'High', color: 'var(--color-errors)', count: 2 },
    { id: 'medium', label: 'Medium', color: 'var(--color-sev-high)', count: 1 },
    { id: 'low', label: 'Low', color: 'var(--color-sev-medium)', count: 1 },
    { id: 'passed', label: 'Passed', color: 'var(--color-sev-low)', count: 14 },
]

export default function SeverityMatrix() {
    return (
        <div className="severity-matrix-grid">
            {severityTiers.map((tier) => (
                <div key={tier.id} className="severity-matrix-box">
                    <div className="severity-matrix-header" style={{ background: tier.color }}>
                        {tier.label}
                    </div>
                    <div className="severity-matrix-count">{tier.count}</div>
                </div>
            ))}
        </div>
    )
}