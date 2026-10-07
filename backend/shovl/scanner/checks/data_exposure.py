import re

import requests

from .. import http

# Fields that should never appear in a public API response
SENSITIVE_FIELDS = [
    "password", "passwd", "secret", "token",
    "api_key", "apikey", "ssn", "credit_card",
    "card_number", "cvv", "private_key"
]

# A "token" in a pagination cursor is not a credential.
PAGINATION_HINTS = ("next", "page", "prev", "cursor", "continuation", "pagination")


def _field_names(node):
    """Every key that appears anywhere in the JSON, split into lowercase words (accessToken -> access_token)."""
    names = set()
    if isinstance(node, dict):
        for key, value in node.items():
            spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
            names.add(re.sub(r"[^a-z0-9]+", "_", spaced.lower()).strip("_"))
            names |= _field_names(value)
    elif isinstance(node, list):
        for item in node:
            names |= _field_names(item)
    return names


def _sensitive_fields(body):
    """The sensitive field names used as keys in the response. Values are ignored."""
    found = []
    names = _field_names(body)
    for field in SENSITIVE_FIELDS:
        for name in names:
            as_word = name == field or name.startswith(field + "_") or name.endswith("_" + field) or f"_{field}_" in name
            if not as_word:
                continue
            if field == "token" and any(hint in name for hint in PAGINATION_HINTS):
                continue
            found.append(field)
            break
    return found


def run(target_url: str, token: str = None, verbose: bool = False, budget=None) -> dict:
    result = {
        "check": "Excessive Data Exposure",
        "id": "API3",
        "severity": "PASS",
        "detail": [],
        "raw": {} if verbose else None
    }

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = http.get(target_url, headers=headers, budget=budget)
        http.require_complete(r)      # a response cut short by the size cap cannot be analysed

        if verbose:
            # result["raw"] = {
            #     "status_code"; r.status_code,
            #     "response_preview": str(r.text)[:500],
            # }
            result["raw"] = {
                "status_code": r.status_code,
                "response_preview": r.text[:500],
            }

        try:
            body = r.json()
        except Exception:
            result["detail"].append("Response is not JSON - skipping field analysis")
            return result
        
        found = _sensitive_fields(body)

        if found:
            result["severity"] = "HIGH"
            result["detail"].append(f"Sensitive fields detected in response: {found}")
        else:
            result["detail"].append("No sensitive fields detected in response")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["reason"] = getattr(e, "reason", "error")
        result["detail"].append(str(e))

    return result