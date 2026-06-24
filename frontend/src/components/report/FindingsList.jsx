import FindingItem from './FindingItem'

// Shared key scheme so Report and FindingsList agree on identity.
// Findings have no stable unique id (the OWASP `id` can repeat), so we key on id + index.
export const findingKey = (item, index) => `${item?.id || 'finding'}-${index}`

// Renders the real findings array from the scan report. Each finding is:
//   { check, id, severity, detail: string[], raw: object|null }
// Open state is a Set held by the parent, so any number of rows can be open at once.
export default function FindingsList({
    findings = [],
    suggestFix,
    openIds,
    onToggle,
    onExpandAll,
    onCollapseAll,
}) {
    if (!findings.length) {
        return (
            <div className="findings-deck">
                <h3 className="findings-deck-title">vulnerability findings</h3>
                <p className="report-meta-line">No findings returned for this scan.</p>
            </div>
        )
    }

    const allKeys = findings.map((item, index) => findingKey(item, index))
    const allOpen = allKeys.every((k) => openIds.has(k))

    return (
        <div className="findings-deck">
            <div className="findings-deck-head">
                <h3 className="findings-deck-title">vulnerability findings</h3>
                <div className="findings-controls">
                    <button
                        type="button"
                        className="findings-control-btn"
                        onClick={() => onExpandAll(allKeys)}
                        disabled={allOpen}
                    >
                        expand all
                    </button>
                    <button
                        type="button"
                        className="findings-control-btn"
                        onClick={onCollapseAll}
                        disabled={openIds.size === 0}
                    >
                        collapse all
                    </button>
                </div>
            </div>

            {findings.map((item, index) => {
                const key = findingKey(item, index)
                return (
                    <FindingItem
                        key={key}
                        item={item}
                        suggestFix={suggestFix}
                        isExpanded={openIds.has(key)}
                        onToggle={() => onToggle(key)}
                    />
                )
            })}
        </div>
    )
}