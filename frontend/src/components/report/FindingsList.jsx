import FindingItem from './FindingItem'

// Renders the real findings array from the scan report. Each finding is:
//   { check, id, severity, detail: string[], raw: object|null }
export default function FindingsList({ findings = [], suggestFix, openFindingId, setOpenFindingId }) {
    const toggleFinding = (id) => {
        setOpenFindingId(openFindingId === id ? null : id)
    }

    if (!findings.length) {
        return (
            <div className="findings-deck">
                <h3 className="findings-deck-title">vulnerability findings</h3>
                <p className="report-meta-line">No findings returned for this scan.</p>
            </div>
        )
    }

    return (
        <div className="findings-deck">
            <h3 className="findings-deck-title">vulnerability findings</h3>

            {findings.map((item, index) => {
                // Findings have no stable unique id of their own; the OWASP-style
                // `id` can repeat, so we key on index + id.
                const key = `${item.id || 'finding'}-${index}`
                return (
                    <FindingItem
                        key={key}
                        item={item}
                        suggestFix={suggestFix}
                        isExpanded={openFindingId === key}
                        onToggle={() => toggleFinding(key)}
                    />
                )
            })}
        </div>
    )
}