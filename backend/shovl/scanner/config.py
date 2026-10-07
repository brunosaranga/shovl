import os

# Per-request timeouts as (connect, read) seconds.
CONNECT_TIMEOUT = float(os.getenv("SHOVL_CONNECT_TIMEOUT", "5"))
READ_TIMEOUT = float(os.getenv("SHOVL_READ_TIMEOUT", "15"))
REQUEST_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

# The rate-limit check fires many requests in a tight loop; keep its read budget
# short so one slow/hanging response can't stall the whole scan for minutes.
RATE_LIMIT_TIMEOUT = (
    CONNECT_TIMEOUT,
    float(os.getenv("SHOVL_RATE_LIMIT_READ_TIMEOUT", "6")),
)

# Total time one scan may spend making requests, in seconds. When it runs out,
# the checks still waiting are recorded as skipped and the report completes
# with what it has.
SCAN_TIME_BUDGET = float(os.getenv("SHOVL_SCAN_TIME_BUDGET", "90"))

# Redirects followed per request before giving up.
MAX_REDIRECTS = int(os.getenv("SHOVL_MAX_REDIRECTS", "5"))

# The most of a response body the scanner will read, in bytes. Anything past
# this is dropped, so a huge or endless response cannot eat memory or time.
MAX_BODY_BYTES = int(os.getenv("SHOVL_MAX_BODY_BYTES", str(1024 * 1024)))

# The longest one response may take to arrive in full, in seconds. This stops a
# target that trickles bytes slowly from holding a request open.
RESPONSE_TIME_CAP = float(os.getenv("SHOVL_RESPONSE_TIME_CAP", "30"))


def allow_private_targets():
    """
    DEVELOPMENT ONLY. When SHOVL_ALLOW_PRIVATE_TARGETS=1 the scanner may reach
    localhost and every other private address, and localhost/127.0.0.1 count as
    practice targets. NEVER set this in production: anyone could then point the
    scanner at your own server and network. Leave it unset or 0.
    """
    return os.getenv("SHOVL_ALLOW_PRIVATE_TARGETS") == "1"