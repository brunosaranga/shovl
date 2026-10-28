import logging

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle

from core.ratelimit import client_address

logger = logging.getLogger(__name__)


class GuestCreationThrottle(AnonRateThrottle):
    """
    Limits how many guest sessions one network address can create.

    Without this, anyone could make a fresh guest for every 3 free scans and walk around the scan allowance.

    Behind a proxy or load balancer (production), set the GUEST_THROTTLE_PROXIES environment variable to the number of proxies in front of Django. Until then every request looks like it comes from the proxy, so the whole site would share one counter. To find the number on a new host, set SHOVL_LOG_CLIENT_IP=1, create a guest from your own browser and read the log line this class writes.
    """

    scope = 'guest_creation'
    rate = '30/hour'            # change the limit here. Per address, rolling window.

    def get_ident(self, request):
        # DRF's own version trusts the whole X-Forwarded-For header when no proxy count is configured, so a script could send a new fake address with evry request and never be counted. Use the real connection address unless we are told how many trusted proxies sit in front of us (core/ratelimit.py, shared with the API's general rate limit).
        proxies = getattr(settings, 'GUEST_THROTTLE_PROXIES', 0)
        remote_addr = request.META.get('REMOTE_ADDR')
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ident = client_address(request.META)

        if getattr(settings, 'SHOVL_LOG_CLIENT_IP', False):
            logger.info(
                'guest creation: REMOTE_ADDR=%s X-Forwarded-For=%s counted as %s (GUEST_THROTTLE_PROXIES=%s)',
                remote_addr, forwarded, ident, proxies,
            )
        return ident

class AccountCreationThrottle(GuestCreationThrottle):
    """
    Limits how many accounts one network address can sign up. Every sign-up emails a code,
    so without this a script could spend xikomu's daily email allowance (and fill strangers'
    inboxes) by signing up with other people's addresses. Same address rules as guests.
    """

    scope = 'account_creation'
    rate = '20/hour'            # per address, rolling window; generous for shared networks


class PasswordResetThrottle(GuestCreationThrottle):
    """
    Limits how many reset codes one network address can ask for, whatever the addresses: the
    form works signed out, so without this a script could use it to send xikomu's email to
    strangers. Each address and account has its own limits too (accounts/reset.py).
    """

    scope = 'password_reset'
    rate = '10/hour'


class PasswordResetConfirmThrottle(GuestCreationThrottle):
    """
    Limits how many reset attempts (code + new password) one network address can make. Each
    code also stops working after 5 wrong tries (accounts/reset.py).
    """

    scope = 'password_reset_confirm'
    rate = '30/hour'
