import dns.resolver
import requests
from urllib.parse import urlparse

ALLOWED_PRACTICE_TARGETS = [
    "httpbin.org",
    "postman-echo.com",
    "localhost",
    "127.0.0.1",
]

def is_practice_target(url: str) -> bool:
    hostname = urlparse(url).hostname
    return any(
        hostname == target or (hostname and hostname.endswith(f".{target}"))
        for target in ALLOWED_PRACTICE_TARGETS
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
        r = requests.get(url, timeout=5)
        return token in r.text
    except Exception:
        return False