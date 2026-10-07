# loads each check dynamically
import importlib
import inspect
import logging

from .http import MESSAGES, ScanRequestError, TimeBudget, get as http_get

logger = logging.getLogger(__name__)

# A list of module paths
CHECKS = [
    "scanner.checks.misconfig",
    "scanner.checks.rate_limit",
    "scanner.checks.bola",
    "scanner.checks.auth",
    "scanner.checks.data_exposure",
    "scanner.checks.mass_assignment",
]

# (name, id) of each check, used when a check cannot run and has no result of its own.
CHECK_INFO = {
    "scanner.checks.misconfig": ("Security Misconfiguration", "API5"),
    "scanner.checks.rate_limit": ("Rate Limiting Absence", "API4"),
    "scanner.checks.bola": ("Broken Object Level Authorization", "API1"),
    "scanner.checks.auth": ("Broken Authentication", "API2"),
    "scanner.checks.data_exposure": ("Excessive Data Exposure", "API3"),
    "scanner.checks.mass_assignment": ("Mass Assignment", "API6"),
}


class ScanFailed(Exception):
    """
    The scan could not produce a usable result. `reason` is a short code and
    `message` is plain language that is safe to show to the user.
    """

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason
        self.message = message


def preflight(target_url, budget=None):
    """
    One request to confirm the target can be reached at all, before any check
    runs. Any HTTP answer counts as reachable, even a 404 or a 500: those are
    answers the checks may find real problems in. Raises ScanFailed when we
    cannot connect, or the target never answers.
    """
    try:
        # Headers only: we do not need the body to know the target answers.
        http_get(target_url, budget=budget, read_body=False)
    except ScanRequestError as e:
        raise ScanFailed(e.reason, e.message)


def run_check(module_path, target_url, token=None, verbose=False, budget=None):
    """
    Run one check and return its finding. Never raises: a check that cannot run
    comes back as an ERROR finding with a message that is safe to show.
    """
    if budget is not None and budget.expired:
        return _error_finding(module_path, MESSAGES["time_limit"], "time_limit")

    try:
        module = importlib.import_module(module_path)  # loads the check dynamically
        kwargs = {}
        # Checks that know about the time budget get it; older ones still work.
        if budget is not None and "budget" in inspect.signature(module.run).parameters:
            kwargs["budget"] = budget
        return module.run(target_url, token, verbose, **kwargs)
    except ScanRequestError as e:
        return _error_finding(module_path, e.message, e.reason)
    except Exception:
        # A bug in a check. Keep the details in the log, not in the report.
        logger.exception("Check %s crashed", module_path)
        return _error_finding(
            module_path, "This check hit an unexpected problem and could not finish.", "check_error"
        )


def _error_finding(module_path, message, reason):
    name, check_id = CHECK_INFO.get(module_path, (module_path, "UNKNOWN"))
    return {
        "check": name,
        "id": check_id,
        "severity": "ERROR",
        "detail": [message],
        "reason": reason,
    }


def ensure_usable(findings):
    """
    Raise ScanFailed when no check produced a real result. A scan like that has
    told the user nothing, so it is saved as failed and does not count against
    their allowance.
    """
    if any(f.get("severity") != "ERROR" for f in findings):
        return

    first = findings[0] if findings else {}
    detail = first.get("detail") or []
    raise ScanFailed(
        first.get("reason", "no_results"),
        detail[0] if detail else "None of the checks could produce a result.",
    )


def build_raw(target_url, findings, verbose=False, suggest_fix=False, generate_report=True):
    """The raw scan result that format_report turns into the report."""
    return {
        "target": target_url,
        "total_checks": len(findings),
        "verbose": verbose,
        "suggest_fix": suggest_fix,
        "generate_report": generate_report,
        "findings": findings,
        "risk_score": _calculate_risk(findings),
    }


def run_scan(
    target_url: str,
    token: str = None,
    verbose: bool = False,
    suggest_fix: bool = False,
    generate_report: bool = True,
) -> dict:
    budget = TimeBudget()

    preflight(target_url, budget=budget)

    results = [
        run_check(module_path, target_url, token, verbose, budget=budget)
        for module_path in CHECKS
    ]

    ensure_usable(results)

    return build_raw(target_url, results, verbose, suggest_fix, generate_report)


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