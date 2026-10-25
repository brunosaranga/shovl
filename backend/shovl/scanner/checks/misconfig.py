import re

import requests

from .. import http

SEVERITY_ORDER = {"PASS": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

# A version number in a header's value: "nginx/1.18.0", "Apache/2.4.41 (Ubuntu)", "PHP/8.1.2".
VERSION = re.compile(r"\d+\.\d+")
# Headers whose only job is to name the software behind a site.
FRAMEWORK_HEADERS = ("X-Powered-By", "X-AspNet-Version", "X-AspNetMvc-Version")


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

        # A Server header that only names the software ("cloudflare", "nginx") is near
        # universal and usually set by a CDN or the host, not the API: nothing to report. One
        # that gives the version tells an attacker which known vulnerabilities to try (LOW).
        server = r.headers.get("Server", "")
        if VERSION.search(server):
            _raise_to(result, "LOW")
            result["detail"].append(f"Server header reveals the software version: {server}")

        for name in FRAMEWORK_HEADERS:
            if r.headers.get(name):
                _raise_to(result, "LOW")
                result["detail"].append(f"{name} header reveals the framework: {r.headers[name]}")

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