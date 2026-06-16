import requests

# Extra fields a client should never be able to set
INJECTED_FIELDS = {
    "is_admin": True,
    "role": "admin",
    "verified": True,
    "balance": 99999,
}

def run(target_url: str, token: str = None, verbose: bool = False) -> dict:
    result = {
        "check": "Mass Assignment",
        "id": "API6",
        "severity": "PASS",
        "detail": [],
        "raw": {} if verbose else None
    }

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        headers["Content-Type"] = "application/json"

        r = requests.post(
            target_url,
            json=INJECTED_FIELDS,
            headers=headers,
            timeout=5
        )

        if verbose:
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
        
        accepted = [k for k in INJECTED_FIELDS if k in body_str]

        if accepted:
            result["severity"] = "HIGH"
            result["detail"].append(f"Server accpeted privileged fields: {accepted}")
        elif r.status_code in [200, 201]:
            result["severity"] = "MEDIUM"
            result["detail"].append("POST accepted but injected fields not confirmed in response")
        else:
            result["detail"].append("Mass assignment not detected")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["detail"].append(str(e))

    return result