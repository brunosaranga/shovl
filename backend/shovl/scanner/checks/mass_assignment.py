# REMINDER: THIS IS THE ONLY CHECK THAT WRITES.
# Every other check only reads. This one POSTs to the target, and on an API with
# a working create endpoint that creates a record on every scan. If the API is
# vulnerable, the record is created with the privileged values below (an admin
# flag, a large balance), in real data we cannot clean up. Verifying that someone
# owns a domain is not their consent to have test data written to it.
#
# So for the beta it runs on PRACTICE TARGETS ONLY (public echo servers, nothing
# to damage). On a user's own domain the engine skips it with the finding
# "not_run" (see WRITE_CHECKS in scanner/engine.py and allow_writes in
# scans/views.py). Do not remove it from WRITE_CHECKS or pass allow_writes=True
# for real domains until an explicit user opt-in exists ("also send a test POST
# that may create a record"). That opt-in is planned after the beta.
import requests

from .. import http

# Extra fields a client should never be able to set
INJECTED_FIELDS = {
    "is_admin": True,
    "role": "admin",
    "verified": True,
    "balance": 99999,
}

# A harmless field no server has a reason to know. If it comes back, the server
# returns whatever it is sent (an echo server, or one that stores any field),
# so a returned field does not show that it was accepted.
CONTROL_FIELD = "shovll_control_field"
CONTROL_VALUE = "shovll-control-value"


def _pairs(node):
    """Every (key, value) pair in a JSON document, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, value
            yield from _pairs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _pairs(item)


def _same_value(returned, sent):
    return returned == sent or str(returned).lower() == str(sent).lower()


def _accepted_fields(body):
    """Injected fields that came back with the very value we sent."""
    pairs = [(str(key).lower(), value) for key, value in _pairs(body)]
    return [
        field for field, sent in INJECTED_FIELDS.items()
        if any(key == field and _same_value(value, sent) for key, value in pairs)
    ]


def run(target_url: str, token: str = None, verbose: bool = False, budget=None) -> dict:
    # Sends a POST. Callers must go through engine.run_check, which only allows
    # this on practice targets (see the reminder at the top of this file).
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

        payload = dict(INJECTED_FIELDS)
        payload[CONTROL_FIELD] = CONTROL_VALUE

        r = http.post(
            target_url,
            json=payload,
            headers=headers,
            budget=budget,
        )
        http.require_complete(r)      # a response cut short by the size cap cannot be analysed

        try:
            body = r.json()
        except Exception:
            if verbose:
                result["raw"] = {
                    "status_code": r.status_code,
                    "response_preview": r.text[:500],
                }
            result["detail"].append("Response is not JSON - skipping field analysis")
            return result

        is_success = 200 <= r.status_code < 300
        accepted = _accepted_fields(body) if is_success else []
        # Searched as text as well, so an echo that returns the body as a string is caught.
        control_returned = is_success and CONTROL_VALUE in r.text

        if verbose:
            result["raw"] = {
                "status_code": r.status_code,
                "response_preview": r.text[:500],
                "accepted": accepted,
                "control_returned": control_returned,
            }

        if control_returned:
            result["severity"] = "LOW"
            result["detail"].append(
                "The server returns whatever it is sent (a made-up control field "
                "came back too), so a returned field does not show it was accepted. "
                "Mass assignment could not be assessed"
            )
        elif accepted:
            result["severity"] = "HIGH"
            result["detail"].append(f"Server accepted privileged fields: {accepted}")
        elif is_success:
            result["severity"] = "MEDIUM"
            result["detail"].append("POST accepted but injected fields not confirmed in response")
        else:
            result["detail"].append("Mass assignment not detected")

    except requests.exceptions.RequestException as e:
        result["severity"] = "ERROR"
        result["reason"] = getattr(e, "reason", "error")
        result["detail"].append(str(e))

    return result