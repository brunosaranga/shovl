"""
The launch list's three endpoints (waitlist/services.py has the rules).

    POST /api/waitlist/           {first_name, email, consent_version, website}   join
    POST /api/waitlist/confirm/   {token}                                         the email's button
    POST /api/waitlist/leave/     {token}                                         "remove me"
"""
from rest_framework import permissions, status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import WaitlistEntry
from .throttles import WaitlistLinkThrottle, WaitlistThrottle

PENDING = (
    "Check your inbox: if this address isn't on the list yet, we've emailed it a link to confirm. "
    "Nothing is sent until its button is pressed."
)
CONFIRMED = "You're on the list: one email when xikomu launches."
CONFIRM_INVALID = {
    "detail": "This link isn't valid any more: it may have been used already, or it's older than 48 hours.",
    "code": "link_invalid",
}
# Leave links never expire, so a bad one was changed or cut short on the way.
LEAVE_INVALID = {
    "detail": "This link isn't valid. Open it again from the email, in full.",
    "code": "link_invalid",
}


class TooManyRequests(Throttled):
    """429 in plain words, with how long to wait."""

    def __init__(self, wait=None):
        super().__init__(wait=wait)
        self.detail = {
            "detail": "Too many requests from your network. Try again in an hour.",
            "code": "too_many_requests",
            "retry_after": self.wait,
        }


class ListView(APIView):
    permission_classes = [permissions.AllowAny]

    def throttled(self, request, wait):
        raise TooManyRequests(wait=wait)


class JoinView(ListView):
    """
    The modal after a first scan. 200 {"status": "pending", "detail"} whatever the address (new,
    pending, already on the list), or {"status": "confirmed"} when a confirmed account asks with
    its own address. 400 for a missing or invalid name or address, or a consent version that
    isn't the current one. A filled-in `website` (a field people never see) gets the pending
    answer and nothing happens.
    """
    throttle_classes = [WaitlistThrottle]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        if str(data.get("website") or "").strip():
            return Response({"status": "pending", "detail": PENDING})
        if data.get("consent_version") != services.CONSENT_VERSION:
            return Response(
                {"consent": ["The wording changed since this page loaded. Reload it and read it again."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user if request.user and request.user.is_authenticated else None
        try:
            outcome = services.join(
                data.get("email"),
                data.get("first_name"),
                WaitlistEntry.SOURCE_AFTER_SCAN,
                signed_in=user,
            )
        except ValueError as problem:
            field = str(problem)
            message = {
                "email": "Enter a valid email address.",
                "first_name": (
                    f"Letters only, with spaces, hyphens or apostrophes between them; at most {services.NAME_MAX}."
                ),
            }[field]
            return Response({field: [message]}, status=status.HTTP_400_BAD_REQUEST)
        if outcome == "confirmed":
            return Response({"status": "confirmed", "detail": CONFIRMED})
        return Response({"status": "pending", "detail": PENDING})


class ConfirmView(ListView):
    """The confirmation page's button. 200 {"done": true}, or 400 link_invalid."""
    authentication_classes = []
    throttle_classes = [WaitlistLinkThrottle]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        if services.confirm(data.get("token")) is None:
            return Response(CONFIRM_INVALID, status=status.HTTP_400_BAD_REQUEST)
        return Response({"done": True})


class LeaveView(ListView):
    """ "remove me": 200 {"done": true} (also if already removed), or 400 link_invalid."""
    authentication_classes = []
    throttle_classes = [WaitlistLinkThrottle]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        if not services.leave(data.get("token")):
            return Response(LEAVE_INVALID, status=status.HTTP_400_BAD_REQUEST)
        return Response({"done": True})
