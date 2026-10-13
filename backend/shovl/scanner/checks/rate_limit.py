import requests
import time

from .. import config, http

BURST_COUNT = 15
BURST_INTERVAL = 0.1 # seconds between requests

# Headers that show a server has a rate limit, even if this short burst did not
# reach it (RateLimit-Limit, X-RateLimit-Remaining, X-Rate-Limit-Limit, ...).
RATE_LIMIT_HEADER_PREFIXES = ("ratelimit", "x-ratelimit", "x-rate-limit")


def _rate_limit_headers(response):
    """The rate-limit headers a response carries, as {name: value}."""
    return {
        name: value
        for name, value in response.headers.items()
        if name.lower().startswith(RATE_LIMIT_HEADER_PREFIXES)
    }


def _describe(headers):
    """One header to show the user, preferring the one that states the limit."""
    for name, value in headers.items():
        if name.lower().endswith("limit"):
            return f"{name}: {value}"
    name, value = next(iter(headers.items()))
    return f"{name}: {value}"


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
        advertised = {}

        for i in range(BURST_COUNT):
            if i:
                time.sleep(BURST_INTERVAL)
            r = http.get(target_url, headers=headers, budget=budget, timeout=config.RATE_LIMIT_TIMEOUT)
            status_codes.append(r.status_code)
            advertised.update(_rate_limit_headers(r))
            if r.status_code == 429:
                break       # the limit was hit; no need to keep sending

        if verbose:
            result["raw"] = {"status_codes": status_codes, "rate_limit_headers": advertised}

        sent = len(status_codes)

        if 429 in status_codes:
            result["detail"].append(f"Rate limiting is active (429 received after {sent} requests)")
        elif advertised:
            result["detail"].append(
                f"No 429 in {sent} requests, but the server advertises a rate limit "
                f"({_describe(advertised)})"
            )
        else:
            # Not proof that there is no limit: many APIs allow far more than
            # this burst before they start refusing.
            result["severity"] = "MEDIUM"
            result["detail"].append(
                f"No rate limiting detected after {sent} rapid requests (no 429 and no "
                "rate-limit headers). The limit may be higher than this test reaches, "
                "so confirm that one exists and add one if it does not"
            )

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["reason"] = getattr(e, "reason", "error")
        result["detail"].append(str(e))

    return result