import requests

from .. import http

SEVERITY_ORDER = {"PASS": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


def _raise_to(result, severity):
    """Only ever make the result worse, so a later, milder finding cannot hide an earlier, worse one."""
    if SEVERITY_ORDER[severity] > SEVERITY_ORDER[result["severity"]]:
        result["severity"] = severity


def run(target_url: str, token: str = None, verbose: bool = False, budget=None) -> dict:
    result = {
        "check": "Security Misconfiguration",
        "id": "API5",
        "severity": "PASS",
        "detail": [],
        "raw": {} if verbose else None
    }

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = http.get(target_url, headers=headers, budget=budget)

        if verbose:
            result["raw"] = {
                "status_code": r.status_code,
                "headers": dict(r.headers),
            }
        
        if not target_url.lower().startswith("https://"):
            _raise_to(result, "HIGH")
            result["detail"].append("API not served over HTTPS")

        if "Server" in r.headers:
            _raise_to(result, "MEDIUM")
            result["detail"].append(f"Server header exposed: {r.headers['Server']}")

        if r.headers.get("Access-Control-Allow-Origin") == "*":
            _raise_to(result, "MEDIUM")
            result["detail"].append("CORS wildcard (*) allows all origins")

        if not result["detail"]:
            result["detail"].append("No misconfigurations detected")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["reason"] = getattr(e, "reason", "error")
        result["detail"].append(str(e))

    return result