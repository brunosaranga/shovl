import requests

# Fields that should never appear in a public API response
SENSITIVE_FIELDS = [
    "password", "passwd", "secret", "token",
    "api_key", "apikey", "ssn", "credit_card",
    "card_number", "cvv", "private_key"
]

def run(target_url: str, token: str = None, verbose: bool = False) -> dict:
    result = {
        "check": "Excessive Data Exposure",
        "id": "API3",
        "severity": "PASS",
        "detail": [],
        "raw": {} if verbose else None
    }

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = requests.get(target_url, headers=headers, timeout=5)

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
            body_str = str(body).lower()
        except Exception:
            result["detail"].append("Response is not JSON - skipping field analysis")
            return result
        
        found = [f for f in SENSITIVE_FIELDS if f in body_str]

        if found:
            result["severity"] = "HIGH"
            result["detail"].append(f"Sensitive fields detected in response: {found}")
        else:
            result["detail"].append("No sensitive fields detected in response")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["detail"].append(str(e))

    return result