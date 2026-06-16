from datetime import datetime, timezone

def format_report(raw: dict) -> dict:
    return {
        "meta": {
            "target": raw["target"],
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "risk_score": raw["risk_score"],
            "total_checks": raw["total_checks"],
            "verbose": raw.get("verbose", False),
            "suggest_fix": raw.get("suggest_fix", False),
        },
        "summary": _build_summary(raw["findings"]),
        "findings": raw["findings"],
    }

def _build_summary(findings: list) -> dict:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "PASS": 0, "ERROR": 0}
    for f in findings:
        severity = f.get("severity", "ERROR")
        counts[severity] = counts.get(severity, 0) + 1
    return counts