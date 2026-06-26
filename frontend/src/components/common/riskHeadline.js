// Single source of truth for presenting the backend's overall risk_score on the
// report. Mirrors the scan-outcome truth table. The backend emits exactly one of:
//   CRITICAL | HIGH | MEDIUM | LOW | INCOMPLETE
//
// INCOMPLETE is NOT a risk level — it means no check completed successfully, so
// we render it in neutral slate (neither alarm-red nor all-clear-green) to avoid
// implying the target is safe when we simply couldn't assess it.

const RISK_STYLES = {
    CRITICAL:   { label: 'CRITICAL',   bg: '#ff4d4f', fg: '#fff' },
    HIGH:       { label: 'HIGH',       bg: '#ff9f43', fg: '#111' },
    MEDIUM:     { label: 'MEDIUM',     bg: '#ffdd59', fg: '#111' },
    LOW:        { label: 'LOW',        bg: '#26de81', fg: '#111' },
    INCOMPLETE: { label: 'INCOMPLETE', bg: '#8395a7', fg: '#fff' },
}

const FALLBACK = { label: '—', bg: '#dfe4ea', fg: '#111' }

export function getRiskHeadline(riskScore) {
    if (!riskScore) return FALLBACK
    return RISK_STYLES[String(riskScore).toUpperCase()] || FALLBACK
}

export default getRiskHeadline