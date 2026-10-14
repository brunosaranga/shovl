import dns.resolver
from urllib.parse import urlparse, urlsplit

from scanner import config, http

# Public APIs built for testing HTTP clients: free, no key, and their writes are echoed
# or simulated (never stored), so a practice scan's test POST harms nobody. Subdomains
# count too (api.postman-echo.com). Keep in sync with PRACTICE_TARGETS in
# frontend/src/lib/targets.js. Left out on purpose: reqres.in (needs an API key),
# api.escuelajs.co (writes are stored for everyone), httpbin.org (no uptime guarantee).
ALLOWED_PRACTICE_TARGETS = [
    "postman-echo.com",
    "httpbingo.org",
    "jsonplaceholder.typicode.com",
    "dummyjson.com",
]

# DEVELOPMENT ONLY (SHOVL_ALLOW_PRIVATE_TARGETS=1): local servers. In production
# these point at our own machine, so they are never practice targets.
LOCAL_PRACTICE_TARGETS = [
    "localhost",
    "127.0.0.1",
]


def practice_targets():
    if config.allow_private_targets():
        return ALLOWED_PRACTICE_TARGETS + LOCAL_PRACTICE_TARGETS
    return list(ALLOWED_PRACTICE_TARGETS)


def is_practice_target(url: str) -> bool:
    hostname = urlparse(url).hostname
    return any(
        hostname == target or (hostname and hostname.endswith(f".{target}"))
        for target in practice_targets()
    )

def verify_dns(hostname: str, token: str) -> bool:
    record = f"_shovl-verify.{hostname}"
    try:
        answers = dns.resolver.resolve(record, "TXT")
        for answer  in answers:
            if token in str(answer):
                return True
    except Exception:
        return False
    return False

def verify_file(hostname: str, token: str) -> bool:
    url = f"https://{hostname}/shovl-verify-{token}.txt"
    try:
        # A hostname that changes the meaning of the URL (an "@", "?" or "#" in it) is not a hostname.
        if urlsplit(url).hostname != hostname.lower():
            return False

        # Through the scanner's request helper: public addresses only, same-site
        # redirects only, and a size cap.
        r = http.get(url)

        # The file must be the token and nothing else. Looking for the token
        # anywhere in the page would let a site that echoes the requested path
        # (a "not found" page, say) pass for a domain it does not own.
        return r.status_code == 200 and r.text.strip() == token
    except Exception:
        return False