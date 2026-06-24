from datetime import datetime, timezone

# Actionable remediation guidance, keyed by the OWASP-style finding id each check
# emits. Attached to non-passing findings only when suggest_fix is enabled.
REMEDIATION = {
    "API1": (  # Broken Object Level Authorization
        "Enforce object-level authorization on every request: confirm the "
        "authenticated user owns or may access the specific object ID instead of "
        "trusting IDs from the client. Prefer random/UUID identifiers and apply "
        "deny-by-default access control."
    ),
    "API2": (  # Broken Authentication
        "Harden authentication: enforce strong passwords and lock/throttle repeated "
        "login attempts, issue short-lived access tokens with secure refresh "
        "rotation, validate token signature and expiry on every request, and only "
        "accept credentials over HTTPS."
    ),
    "API3": (  # Excessive Data Exposure
        "Return only the fields each client needs. Define explicit response "
        "serializers/schemas rather than returning whole objects, and strip "
        "sensitive fields (tokens, emails, internal IDs) server-side instead of "
        "relying on the client to hide them."
    ),
    "API4": (  # Rate Limiting Absence
        "Add per-client/IP/token rate limiting and throttling (sliding window or "
        "token bucket), respond with 429 and a Retry-After header when exceeded, and "
        "cap page sizes and payload sizes to prevent resource exhaustion."
    ),
    "API5": (  # Security Misconfiguration
        "Remove or mask revealing headers (Server, X-Powered-By), disable verbose "
        "error output in production, enforce HTTPS with HSTS, restrict CORS to known "
        "origins, and keep frameworks and dependencies patched."
    ),
    "API6": (  # Mass Assignment
        "Bind requests to explicit allow-listed fields (DTOs/serializer field lists) "
        "instead of mapping the request body straight onto your models. Never let "
        "clients set privileged attributes such as role, is_admin, or ownership keys."
    ),
}


def format_report(raw: dict) -> dict:
    suggest_fix = raw.get("suggest_fix", False)
    findings = raw["findings"]

    if suggest_fix:
        for f in findings:
            severity = (f.get("severity") or "").upper()
            if severity in ("PASS", "ERROR"):
                continue
            if not f.get("remediation"):
                fix = REMEDIATION.get(f.get("id"))
                if fix:
                    f["remediation"] = fix

    return {
        "meta": {
            "target": raw["target"],
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "risk_score": raw["risk_score"],
            "total_checks": raw["total_checks"],
            "verbose": raw.get("verbose", False),
            "suggest_fix": suggest_fix,
            "generate_report": raw.get("generate_report", True),
        },
        "summary": _build_summary(findings),
        "findings": findings,
    }


def _build_summary(findings: list) -> dict:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "PASS": 0, "ERROR": 0}
    for f in findings:
        severity = f.get("severity", "ERROR")
        counts[severity] = counts.get(severity, 0) + 1
    return counts