"""
"Since your last scan": what changed between a scan and the one before it.

The scan before is the newest *complete* scan by the same person of the same address,
started earlier. "Same address" ignores http vs https, a default port, the case of the host
name and a trailing slash, so moving an API to HTTPS still compares with its old scans.
Failed, interrupted and stopped scans have no results, so they are skipped.

Every check returns exactly one finding, so checks are matched by their OWASP id (API1..API6):

    fixed          a problem before, PASS now
    new            PASS before, a problem now
    better         still a problem, at a lower severity
    worse          a problem at a higher severity
    same           same severity as before
    not_compared   the check ran in one of the two scans only (could not run in the other)

A check that could not run in either scan (mass assignment on your own domain) is left out.
The report page and the PDF both show this (frontend: sections/report/SinceLastScan).
"""
from urllib.parse import urlsplit

from django.db.models import Q

from .models import Scan

# Severities in order. ERROR means the check did not run, so it has no place on this scale.
RANK = {"PASS": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

# How many of the person's earlier scans are looked through for one of the same address.
LOOKBACK = 200

CHANGES = ("fixed", "new", "better", "worse", "same", "not_compared")


def target_key(url):
    """The parts of an address that make it "the same API": host, port unless default, path, query."""
    try:
        parts = urlsplit((url or "").strip())
        port = parts.port
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    if not host:
        return None
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    return (netloc, parts.path.rstrip("/"), parts.query)


def previous_scan(scan):
    """The newest complete scan before this one, by the same person, of the same address. Or None."""
    key = target_key(scan.target_url)
    if key is None:
        return None

    # A cheap first filter in the database; target_key decides.
    host = urlsplit(scan.target_url.strip()).hostname or ""
    earlier = (
        Scan.objects.filter(user_id=scan.user_id, status="complete", target_url__icontains=host)
        .filter(Q(created_at__lt=scan.created_at) | Q(created_at=scan.created_at, pk__lt=scan.pk))
        .exclude(pk=scan.pk)
        .order_by("-created_at", "-pk")
        .values_list("pk", "target_url")[:LOOKBACK]
    )
    for pk, url in earlier:
        if target_key(url) == key:
            return Scan.objects.filter(pk=pk).first()
    return None


def _severity(finding):
    return str((finding or {}).get("severity") or "").upper() or None


def _findings_by_id(results):
    findings = (results or {}).get("findings") or []
    return {f.get("id"): f for f in findings if isinstance(f, dict) and f.get("id")}


def _change(before, after):
    if before not in RANK or after not in RANK:
        return "not_compared"
    if before == after:
        return "same"
    if before == "PASS":
        return "new"
    if after == "PASS":
        return "fixed"
    return "better" if RANK[after] < RANK[before] else "worse"


def compare(previous_results, current_results):
    """
    Check by check: {"checks": [{id, check, before, after, change}], "counts": {change: n}}.
    Checks are listed in the current report's order; one only the earlier scan had comes last.
    """
    before = _findings_by_id(previous_results)
    after = _findings_by_id(current_results)
    order = list(after) + [check_id for check_id in before if check_id not in after]

    checks = []
    for check_id in order:
        old, new = before.get(check_id), after.get(check_id)
        old_severity, new_severity = _severity(old), _severity(new)
        # Could not run (or did not exist) on both sides: nothing to say about it.
        if old_severity not in RANK and new_severity not in RANK:
            continue
        checks.append({
            "id": check_id,
            "check": (new or old).get("check") or check_id,
            "before": old_severity,
            "after": new_severity,
            "change": _change(old_severity, new_severity),
        })

    counts = {change: 0 for change in CHANGES}
    for item in checks:
        counts[item["change"]] += 1
    return {"checks": checks, "counts": counts}


def comparison_for(scan):
    """
    What the report shows under "since your last scan", or None when there is nothing to
    compare with (the first complete scan of this address, or a scan that did not complete).
    """
    if scan.status != "complete" or not scan.results:
        return None
    earlier = previous_scan(scan)
    if earlier is None or not earlier.results:
        return None

    meta = (earlier.results or {}).get("meta") or {}
    result = compare(earlier.results, scan.results)
    result["previous"] = {
        "id": earlier.pk,
        "target_url": earlier.target_url,
        "scanned_at": meta.get("scanned_at") or (earlier.completed_at or earlier.created_at).isoformat(),
        "risk_score": earlier.risk_score or meta.get("risk_score") or "",
    }
    result["risk"] = {
        "before": earlier.risk_score or meta.get("risk_score") or "",
        "after": scan.risk_score or ((scan.results or {}).get("meta") or {}).get("risk_score") or "",
    }
    return result
