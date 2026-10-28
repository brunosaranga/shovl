from rest_framework.throttling import SimpleRateThrottle

from core.ratelimit import client_address


class WaitlistThrottle(SimpleRateThrottle):
    """
    Requests to join, per network address, signed in or not (guest sessions are cheap to make,
    so DRF's anonymous-only throttles wouldn't count them). Each address also gets at most one
    confirmation email a day (waitlist/services.py).
    """

    scope = "waitlist"
    rate = "10/hour"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": client_address(request.META) or "unknown"}


class WaitlistLinkThrottle(WaitlistThrottle):
    """Presses of the confirm and remove-me buttons, per network address."""

    scope = "waitlist_link"
    rate = "30/hour"
