import requests

# BOLA: swap object IDs in URL to check if another user's data is returned
PROBE_IDS = [1, 2, 3, 99, 100]

def run(target_url: str, token: str = None, verbose: bool = False) -> dict:
    result = {
        "check": "Broken Object Level Authorization",
        "id": "API1",
        "severity": "PASS",
        "detail": [],
        "raw": [] if verbose else None
    }

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        suspicious = []

        for probe_id in PROBE_IDS:
            probe_url = f"{target_url.rstrip('/')}/{probe_id}"
            r = requests.get(probe_url, headers=headers, timeout=5)

            if verbose:
                result["raw"].append({
                    "url": probe_url,
                    "status_code": r.status_code,
                })

            # 200 arbitrary IDs without auth is suspicious
            if r.status_code == 200 and not token:
                suspicious.append(probe_url)

        if suspicious:
            result["severity"] = "HIGH"
            result["detail"].append(
                f"Object IDs accessible without authorization: {suspicious}"
            )
        else:
            result["detail"].append("No BOLA indicators detected")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["detail"].append(str(e))

    return result