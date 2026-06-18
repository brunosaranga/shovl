import requests
import time

BURST_COUNT = 15
BURST_INTERVAL = 0.1 # seconds between requests

def run(target_url: str, token: str = None, verbose: bool = False) -> dict:
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
            r = requests.get(target_url, headers=headers, timeout=5)
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

    except requests.exception.RequestException as e:
        result["severity"] = "ERROR"
        result["detail"].append(str(e))

    return result