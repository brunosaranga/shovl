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