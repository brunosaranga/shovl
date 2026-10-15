from urllib.parse import urlsplit

# Matches Scan.target_url's max_length. Postgres refuses longer text (SQLite stored it anyway).
MAX_URL_LENGTH = 2048

REQUIRED_MESSAGE = "target_url is required."
FORMAT_MESSAGE = "Invalid URL format. Include http:// or https://"


def target_url_error(value):
    """
    None when value can be scanned and stored, otherwise the message for a 400.
    Checked before any lookup, network activity or database write.
    """
    if not value:
        return REQUIRED_MESSAGE
    if not isinstance(value, str):
        return FORMAT_MESSAGE
    if len(value) > MAX_URL_LENGTH:
        return f"That URL is too long. The limit is {MAX_URL_LENGTH} characters."
    # Control characters (NUL above all) and broken Unicode cannot be stored in Postgres.
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return "That URL contains characters that are not allowed."
    try:
        value.encode("utf-8")
        parsed = urlsplit(value)
    except (UnicodeEncodeError, ValueError):
        return FORMAT_MESSAGE
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return FORMAT_MESSAGE
    return None
