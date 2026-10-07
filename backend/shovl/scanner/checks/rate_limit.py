import requests
import time

from .. import config, http

BURST_COUNT = 15
BURST_INTERVAL = 0.1 # seconds between requests

def run(target_url: str, token: str = None, verbose: bool = False, budget=None) -> dict:
    result = {
        "check": "Rate Limiting Absence",
        "id": "API4",
        "severity": "PASS",
        "detail": [],
        "raw": {} if verbose else None
    }

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        status_codes = []

        for _ in range(BURST_COUNT):
            r = http.get(target_url, headers=headers, budget=budget, timeout=config.RATE_LIMIT_TIMEOUT)
            status_codes.append(r.status_code)
            time.sleep(BURST_INTERVAL)

        if verbose:
            result["raw"] = {"status_codes": status_codes}

        if 429 not in status_codes:
            result["severity"] = "HIGH"
            result["detail"].append(
                f"No rate limiting detected after {BURST_COUNT} rapid requests"
            )
        else:
            result["detail"].append("Rate limiting is active (429 received)")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["reason"] = getattr(e, "reason", "error")
        result["detail"].append(str(e))

    return result