// Maps backend values to the "tone" that ui/Badge and friends colour by.
// One mapping for the whole app, so the same severity never shows in two colours.

const SEVERITY_TONES = {
    CRITICAL: "critical",
    HIGH: "high",
    MEDIUM: "medium",
    LOW: "low",
    PASS: "pass",
    ERROR: "error", // the check could not run: neutral, never alarm-red
};

const RISK_TONES = {
    ...SEVERITY_TONES,
    INCOMPLETE: "incomplete", // nothing could be assessed: neutral, never all-clear green
};

const STATUS_TONES = {
    pending: "accent",
    running: "accent",
    complete: "neutral",
    failed: "danger",
    interrupted: "neutral",
};

const upper = (value) => String(value || "").toUpperCase();

export const severityTone = (severity) => SEVERITY_TONES[upper(severity)] || "error";
export const riskTone = (risk) => RISK_TONES[upper(risk)] || "neutral";
export const statusTone = (status) => STATUS_TONES[status] || "neutral";

/** The order findings and counts are shown in. */
export const SEVERITY_ORDER = ["HIGH", "MEDIUM", "LOW", "PASS", "ERROR"];

/** Scans that finished one way or another. */
export const isFinished = (status) => ["complete", "failed", "interrupted"].includes(status);

/** Findings whose check could not run (severity ERROR), for the coverage note. */
export const checksNotRun = (findings = []) =>
    findings.filter((finding) => upper(finding.severity) === "ERROR");
