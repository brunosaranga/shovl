import requests

from .. import http

def run(target_url: str, token: str = None, verbose: bool = False, budget=None) -> dict:
    result = {
        "check": "Broken Authentication",
        "id": "API2",
        "severity": "PASS",
        "detail": [],
        "raw": {} if verbose else None
    }

    try:
        # Test 1: access without any token
        r_no_auth = http.get(target_url, budget=budget)

        # Test 2: access with a malformed token
        bad_headers = {"Authorization": f"Bearer invalidtoken123"}
        r_bad_auth = http.get(target_url, headers=bad_headers, budget=budget)

        if verbose:
            result["raw"] = {
                "no_auth_status": r_no_auth.status_code,
                "bad_auth_status": r_bad_auth.status_code,
            }

        if r_no_auth.status_code == 200:
            result["severity"] = "HIGH"
            result["detail"].append("Endpoint accessible with no authentication")

        if r_bad_auth.status_code == 200:
            result["severity"] = "HIGH"
            result["detail"].append("Endpoint accessible with invalid token")

        if not result["detail"]:
            result["detail"].append("Authentication controls appear to be in place")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["reason"] = getattr(e, "reason", "error")
        result["detail"].append(str(e))

    return result