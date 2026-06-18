import requests

def run(target_url: str, token: str = None, verbose: bool = False) -> dict:
    result = {
        "check": "Security Misconfiguation",
        "id": "API5",
        "severity": "PASS",
        "detail": [],
        "raw": {} if verbose else None
    }

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = requests.get(target_url, headers=headers, timeout=5)

        if verbose:
            result["raw"] = {
                "status_code": r.status_code,
                "headers": dict(r.headers),
            }
        
        if not target_url.startswith("https://"):
            result["severity"] = "HIGH"
            result["detail"].append("API not served over HTTPS")

        if "Server" in r.headers:
            result["severity"] = "MEDIUM"
            result["detail"].append(f"Server header exposed: {r.headers['Server']}")

        if r.headers.get("Access-Control-Allow-Origin") == "*":
            result["severity"] = "MEDIUM"
            result["detail"].append("CORS wildcard (*) allows all origins")

        if not result["detail"]:
            result["detail"].append("No misconfigurations detected")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["detail"].append(str(e))

    return result