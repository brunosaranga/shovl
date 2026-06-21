// A single accordion row inside the findings deck.
export default function FindingItem({ item, isExpanded, onToggle }) {
    return (
        <div className="finding-item-card">
            <div
                className={`finding-item-header ${isExpanded ? 'expanded' : ''}`}
                onClick={onToggle}
            >
                <div className="finding-title-block">
                    <span
                        className="finding-badge-inline"
                        style={{ backgroundColor: item.color }}
                    >
                        {item.severity}
                    </span>
                    <span className="finding-name-text">{item.title}</span>
                </div>
                <div className="finding-meta-aside">
                    <span className="finding-path-label">{item.path}</span>
                    <span className="finding-caret">{isExpanded ? '▲' : '▼'}</span>
                </div>
            </div>

            {isExpanded && (
                <div className="finding-expanded-body">
                    <p className="finding-description-para">{item.desc}</p>
                    <div className="finding-code-container">
                        <span className="finding-code-header">Vulnerable Code Segment</span>
                        <pre className="finding-code-block">
                            <code>{item.code}</code>
                        </pre>
                    </div>
                    <div className="finding-remediation-tip">
                        <strong>remediation suggestion:</strong> Clean target variables via specialized input filtering routines or abstract operations beneath parameter-driven prepared data layer models.
                    </div>
                </div>
            )}
        </div>
    )
}