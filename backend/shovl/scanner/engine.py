# loads each check dynamically
import importlib

# A list of module paths
CHECKS = [
    "scanner.checks.misconfig",
    "scanner.checks.rate_limit",
    "scanner.checks.bola",
    "scanner.checks.auth",
    "scanner.checks.data_exposure",
    "scanner.checks.mass_assignment",
]

def run_scan(
    target_url: str,
    token: str = None,
    verbose: bool = False,
    suggest_fix: bool = False,
    generate_report: bool = True,
) -> dict:
    results = []

    for module_path in CHECKS:
        try:
            module = importlib.import_module(module_path) # loads each check dynamically
            result = module.run(target_url, token)
        except Exception as e:
            result = {
                "check": module_path,
                "id": "UNKNOWN",
                "severity": "ERROR",
                "detail": [f"Check failed to run: {str(e)}"]
            }
        results.append(result)

    return {
        "target": target_url,
        "total_checks": len(results),
        "verbose": verbose,
        "suggest_fix": suggest_fix,
        "generate_report": generate_report,
        "findings": results,
        "risk_score": _calculate_risk(results),
    }


def _calculate_risk(findings: list) -> str:
    """Overall risk = the single most severe finding that actually ran.

    This is the industry-standard model (Qualys, Tenable, Snyk, Burp all work
    this way): your posture is driven by your worst exposure, not by a sum that
    can read 'CRITICAL' when no individual finding is critical. By construction
    the headline severity always appears in the findings list, so the report
    never contradicts itself.

    ERROR means a check *failed to run*, not that the endpoint is clean. So an
    errored check never counts as a successful assessment. If no check completed
    successfully (every finding errored, or there are none), we can't claim any
    risk level and return INCOMPLETE. Reporting LOW there would be a false
    reassurance — the most dangerous failure mode for a security tool.

    Among completed checks, PASS does not raise the score. A clean scan
    (everything PASS) reports LOW.
    """
    severity_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    rank_to_label = {0: "LOW", 1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}

    completed = [f for f in findings if f.get("severity") != "ERROR"]
    if not completed:
        return "INCOMPLETE"

    worst = max(
        (severity_rank.get(f.get("severity"), 0) for f in completed),
        default=0,
    )
    return rank_to_label[worst]