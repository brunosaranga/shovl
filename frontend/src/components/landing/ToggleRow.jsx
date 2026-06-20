import React from 'react'
import KnobToggle from '../scan/KnobToggle'

// The three scan-option knobs, grouped as one row so Landing doesn't
// need to know KnobToggle's layout details (offsets, ordering, etc).
export default function ToggleRow({
    verbose, setVerbose,
    generateReport, setGenerateReport,
    suggestFix, setSuggestFix,
}) {
    return (
        <div className='toggle-row-container'>
            <KnobToggle label="verbose" active={verbose} onChange={setVerbose} offsetY={0} />
            <KnobToggle label="generate report" active={generateReport} onChange={setGenerateReport} offsetY={40} />
            <KnobToggle label="suggest fix" active={suggestFix} onChange={setSuggestFix} offsetY={80} />
        </div>
    )
}