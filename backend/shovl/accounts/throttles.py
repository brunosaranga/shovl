from django.conf import settings
from rest_framework.throttling import AnonRateThrottle

class GuestCreationThrottle(AnonRateThrottle):
    """
    Limits how many guest sessions one network address can create.

    Without this, anyone could make a fresh guest for every 3 free scans and walk around the scan allowance.

    Behind a proxy or load balancer (production), set GUEST_THROTTLE_PROXIES in settings.py to the number of proxies in front of Django. Until then every request looks like it mcomes from the proxy, so the whole site would share one counter.
    """

    scope = 'guest_creation'
    rate = '30/hour'            # change the limit here. Per address, rolling window.

    def get_ident(self, request):
        # DRF's own version trusts the whole X-Forwarded-For header when no proxy count is configured, so a script could send a new fake address with evry request and never be counted. Use the real connection address unless we are told how many trusted proxies sit in front of us.
        proxies = getattr(settings, 'GUEST_THROTTLE_PROXIES', 0)
        remote_addr = request.META.get('REMOTE_ADDR')
        forwarded = request.META.GET('HTTP_X_FORWARDED_FOR')

        if proxies == 0 or not forwarded:
            return remote_addr


        # Each trusted proxy appends the address it saw. Count back from the end, so anything the client wrote at the front is ignored.
        addresses = [a.strip() for a in forwarded.split(',')]
        return addresses[-min(proxies, len(addresses))]