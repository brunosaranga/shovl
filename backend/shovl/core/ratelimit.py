"""
A general limit on how many requests one client address can send to the API: every route,
the API's own views and anything else (a mistyped path's 404 included).

    - every answer says where the client stands, in the RateLimit-Limit, RateLimit-Remaining
      and RateLimit-Reset headers (seconds until the count starts again), so clients and
      scanners can see that a limit exists before they reach it
    - past the limit: 429, a Retry-After header and {"error", "code": "rate_limited",
      "retry_after"}, the shape the frontend already reads (lib/apiErrors.js)

The limit is settings.SHOVL_API_RATE_LIMIT_PER_MINUTE (API_RATE_LIMIT_PER_MINUTE in the
environment; 0 turns it off). Counted in fixed one-minute windows, in each gunicorn process's
own memory rather than the shared database cache: a counter write on every request would keep
the database awake for every bot that knocks. So with WEB_CONCURRENCY=2 a client can get up to
twice the number before seeing a 429. It is a guard against floods and scripts, not an
allowance: the scan allowance (scans/limits.py) and the per-view throttles (guest sessions,
PDFs, feedback) are counted exactly, in the shared cache.

The host's health check never reaches this (core/health.py answers it first), and the browsers'
CORS preflights are answered before it (corsheaders), so neither counts.
"""
import math
import threading
import time

from django.conf import settings
from django.http import JsonResponse

WINDOW_SECONDS = 60
MESSAGE = "Too many requests from your network. Wait a minute and try again."


def client_address(meta):
    """
    The address a request came from, as the server can trust it.

    Behind a proxy or load balancer (production), GUEST_THROTTLE_PROXIES says how many proxies
    sit in front of Django. Each appends the address it saw to X-Forwarded-For, so count back
    from the end and ignore anything the client wrote at the front: a script can't get a fresh
    counter by sending a made-up address. With 0 (development), the connection's own address.
    """
    proxies = getattr(settings, "GUEST_THROTTLE_PROXIES", 0)
    remote_addr = meta.get("REMOTE_ADDR")
    forwarded = meta.get("HTTP_X_FORWARDED_FOR")
    if proxies == 0 or not forwarded:
        return remote_addr
    addresses = [address.strip() for address in forwarded.split(",")]
    return addresses[-min(proxies, len(addresses))]


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._lock = threading.Lock()
        self._window = None  # when the current minute started (seconds since the epoch)
        self._counts = {}  # address -> requests in the current minute

    def _count(self, address, now):
        """Add one request for this address; returns (count, seconds until the reset)."""
        window = math.floor(now / WINDOW_SECONDS) * WINDOW_SECONDS
        with self._lock:
            if window != self._window:
                # A new minute: start every count again (this also forgets old addresses).
                self._window = window
                self._counts = {}
            count = self._counts.get(address, 0) + 1
            self._counts[address] = count
        reset = max(1, math.ceil(window + WINDOW_SECONDS - now))
        return count, reset

    def __call__(self, request):
        limit = getattr(settings, "SHOVL_API_RATE_LIMIT_PER_MINUTE", 0)
        if limit <= 0:
            return self.get_response(request)

        count, reset = self._count(client_address(request.META) or "unknown", time.time())
        if count > limit:
            response = JsonResponse(
                {"error": MESSAGE, "code": "rate_limited", "retry_after": reset},
                status=429,
            )
            response["Retry-After"] = str(reset)
        else:
            response = self.get_response(request)

        response["RateLimit-Limit"] = str(limit)
        response["RateLimit-Remaining"] = str(max(0, limit - count))
        response["RateLimit-Reset"] = str(reset)
        return response
