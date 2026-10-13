import requests

from .. import evidence, http

# A token that is not valid for any API.
BAD_TOKEN = "invalidtoken123"

SEVERITY_RANK = {"PASS": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


def _flag(result, severity, message):
    """Record a finding. The result keeps the worst severity it has seen."""
    if SEVERITY_RANK[severity] > SEVERITY_RANK[result["severity"]]:
        result["severity"] = severity
    result["detail"].append(message)


def _assess(result, no_auth, bad_auth, with_token):
    # An invalid token that gets through when no token does not: the endpoint
    # checks that a token is present but not that it is valid.
    if evidence.is_rejected(no_auth) and evidence.serves_data(bad_auth):
        _flag(
            result, "HIGH",
            "Accepts an invalid token: a request with no token is refused, "
            "but a request with a made-up token gets through",
        )

    if not evidence.is_open(no_auth):
        # Refused (401/403) is a real answer about authentication. Anything else
        # (not found, a server error, a method that is not allowed) says nothing
        # about it, and must not read as "authentication is in place".
        if not evidence.is_rejected(no_auth):
            if no_auth.status_code in (404, 410):
                reason = f"Nothing was found at this URL ({no_auth.status_code})"
            else:
                reason = f"The endpoint answered {no_auth.status_code} without a token"
            _flag(
                result, "LOW",
                f"Authentication could not be assessed: {reason}. "
                "Check that the URL points at a working endpoint",
            )
        return

    if evidence.is_html(no_auth):
        _flag(
            result, "LOW",
            "Returned a web page instead of API data, so authentication could "
            "not be assessed. Check that the URL points at an API endpoint",
        )
        return

    token_works = with_token is not None and evidence.is_open(with_token)

    # Your own token gets exactly the same answer as no token at all.
    if token_works and evidence.same_body(no_auth, with_token):
        _flag(
            result, "HIGH",
            "Authentication is not enforced: the response is the same with "
            "your token as with no token at all",
        )
        return

    # Open to anyone. The scanner cannot know whether that is intended.
    _flag(
        result, "MEDIUM",
        "Open to anyone: this endpoint responds without a token. That is "
        "expected if it is meant to be public. If it is not, require authentication",
    )
    if evidence.is_rejected(bad_auth):
        result["detail"].append(
            "Invalid tokens are refused, so authentication is optional on this endpoint"
        )
    if token_works:
        result["detail"].append(
            "It returns different content with your token, so some data is protected"
        )
    elif with_token is not None:
        result["detail"].append(
            "Your token did not get a successful response, so protected "
            "content could not be compared"
        )


def run(target_url: str, token: str = None, verbose: bool = False, budget=None) -> dict:
    result = {
        "check": "Broken Authentication",
        "id": "API2",
        "severity": "PASS",
        "detail": [],
        "raw": {} if verbose else None
    }

    try:
        # Access without any token
        no_auth = http.get(target_url, budget=budget)

        # Access with a made-up token
        bad_headers = {"Authorization": f"Bearer {BAD_TOKEN}"}
        bad_auth = http.get(target_url, headers=bad_headers, budget=budget)

        # Access with the token the user supplied, to compare against
        with_token = None
        if token:
            with_token = http.get(
                target_url, headers={"Authorization": f"Bearer {token}"}, budget=budget
            )

        if verbose:
            result["raw"] = {
                "no_auth_status": no_auth.status_code,
                "bad_auth_status": bad_auth.status_code,
            }
            if with_token is not None:
                result["raw"]["token_status"] = with_token.status_code

        _assess(result, no_auth, bad_auth, with_token)

        if not result["detail"]:
            result["detail"].append("Authentication controls appear to be in place")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["reason"] = getattr(e, "reason", "error")
        result["detail"].append(str(e))

    return result