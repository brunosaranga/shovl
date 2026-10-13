import requests

from .. import evidence, http

# BOLA: swap object IDs in the URL to check whether objects are returned
PROBE_IDS = [1, 2, 3, 99, 100]

# An ID that cannot exist. If the server answers it like the others, it is not
# looking objects up by ID at all.
BASELINE_ID = 987654321


def run(target_url: str, token: str = None, verbose: bool = False, budget=None) -> dict:
    result = {
        "check": "Broken Object Level Authorization",
        "id": "API1",
        "severity": "PASS",
        "detail": [],
        "raw": [] if verbose else None
    }

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        base = target_url.rstrip("/")

        # Probe URL -> the JSON object it returned
        readable = {}

        for probe_id in PROBE_IDS:
            probe_url = f"{base}/{probe_id}"
            r = http.get(probe_url, headers=headers, budget=budget)

            if verbose:
                result["raw"].append({
                    "url": probe_url,
                    "status_code": r.status_code,
                })

            body = evidence.json_body(r) if evidence.is_open(r) else None
            if body is not None:
                readable[probe_url] = body

        if not readable:
            result["detail"].append("No BOLA indicators detected")
            return result

        # Only worth a request when something came back.
        baseline_url = f"{base}/{BASELINE_ID}"
        baseline = http.get(baseline_url, headers=headers, budget=budget)
        if verbose:
            result["raw"].append({
                "url": baseline_url,
                "status_code": baseline.status_code,
                "baseline": True,
            })

        bodies = list(readable.values())
        urls = ", ".join(readable)

        if evidence.is_open(baseline):
            # An ID that cannot exist gets the same kind of answer: catch-all
            # or echo server, not objects looked up by ID.
            result["detail"].append(
                "The server answers an ID that cannot exist the same way as the "
                "others, so it does not appear to look objects up by ID. "
                "No evidence of object-level access"
            )
        elif len(bodies) > 1 and all(body == bodies[0] for body in bodies):
            result["detail"].append(
                "Every ID returned the identical response, so it is not "
                "per-object data. No evidence of object-level access"
            )
        elif token:
            result["severity"] = "LOW"
            result["detail"].append(
                f"Objects were returned for these IDs with your token: {urls}. "
                "One account cannot show whether they belong to someone else. "
                "Test with a second account's token to confirm"
            )
        else:
            result["severity"] = "MEDIUM"
            result["detail"].append(
                f"Objects readable by ID without logging in: {urls}. "
                "That is expected if the data is public. If it is not, "
                "require authorization"
            )

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["reason"] = getattr(e, "reason", "error")
        result["detail"].append(str(e))

    return result