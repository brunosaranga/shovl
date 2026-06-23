// A single accordion row inside the findings deck, mapped to the real finding shape:
//   { check, id, severity, detail: string[], raw: object|null }
const SEVERITY_COLORS = {
    HIGH:   'var(--color-sev-high)',
    MEDIUM: 'var(--color-sev-medium)',
    LOW:    'var(--color-sev-low)',
    PASS:   'var(--color-sev-low)',
    ERROR:  'var(--color-errors)',
}

export default function FindingItem({ item, suggestFix, isExpanded, onToggle }) {
    const severity = (item.severity || 'ERROR').toUpperCase()
    const color = SEVERITY_COLORS[severity] || 'var(--color-sev-low)'
    const details = Array.isArray(item.detail) ? item.detail : (item.detail ? [item.detail] : [])
    const hasRaw = item.raw && Object.keys(item.raw).length > 0

    return (
        <div className="finding-item-card">
            <div
                className={`finding-item-header ${isExpanded ? 'expanded' : ''}`}
                onClick={onToggle}
            >
                <div className="finding-title-block">
                    <span className="finding-badge-inline" style={{ backgroundColor: color }}>
                        {severity.toLowerCase()}
                    </span>
                    <span className="finding-name-text">{item.check}</span>
                </div>
                <div className="finding-meta-aside">
                    <span className="finding-path-label">{item.id}</span>
                    <span className="finding-caret">{isExpanded ? '▲' : '▼'}</span>
                </div>
            </div>

            {isExpanded && (
                <div className="finding-expanded-body">
                    {details.length > 0 ? (
                        <ul className="finding-detail-list">
                            {details.map((line, i) => (
                                <li key={i} className="finding-description-para">{line}</li>
                            ))}
                        </ul>
                    ) : (
                        <p className="finding-description-para">No additional detail.</p>
                    )}

                    {hasRaw && (
                        <div className="finding-code-container">
                            <span className="finding-code-header">Raw response data (verbose)</span>
                            <pre className="finding-code-block">
                                <code>{JSON.stringify(item.raw, null, 2)}</code>
                            </pre>
                        </div>
                    )}

                    {/* The current backend checks don't return remediation text, even
                        when suggest_fix is on. Only render the slot if/when they do. */}
                    {suggestFix && item.remediation && (
                        <div className="finding-remediation-tip">
                            <strong>remediation suggestion:</strong> {item.remediation}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}