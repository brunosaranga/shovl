"""
Small helpers the checks use to judge a response, so that a check looks at what
came back and not only at the status code.
"""


def is_open(response):
    """The request was answered with a success status (2xx)."""
    return 200 <= response.status_code < 300


def is_rejected(response):
    """The request was refused for lack of valid credentials."""
    return response.status_code in (401, 403)


def is_html(response):
    """A web page rather than API data (a login page, a single-page app)."""
    content_type = response.headers.get("Content-Type", "").lower()
    if "html" in content_type:
        return True
    start = (response.text or "").lstrip()[:20].lower()
    return start.startswith(("<!doctype html", "<html"))


def serves_data(response):
    """A success response that carries API data, not a web page."""
    return is_open(response) and not is_html(response)


def json_body(response):
    """
    The response body as a non-empty JSON object or list, or None when it is
    anything else (HTML, plain text, empty, a bare number, or a body that was
    cut short by the size cap).
    """
    if getattr(response, "truncated", False):
        return None
    try:
        body = response.json()
    except Exception:
        return None
    return body if isinstance(body, (dict, list)) and body else None


def same_body(first, second):
    """Both responses carry the same content. A body cut short never counts."""
    if getattr(first, "truncated", False) or getattr(second, "truncated", False):
        return False
    first_json, second_json = json_body(first), json_body(second)
    if first_json is not None and second_json is not None:
        return first_json == second_json
    return (first.text or "").strip() == (second.text or "").strip()