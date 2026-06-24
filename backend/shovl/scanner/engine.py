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
    severity_map = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "PASS": 0}
    score = sum(severity_map.get(f['severity'], 0) for f in findings)

    if score >= 7: return "CRITICAL"
    elif score >= 4: return "HIGH"
    elif score >= 2: return "MEDIUM"
    return "LOW"