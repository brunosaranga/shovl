# from django.shortcuts import render
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from scans.limits import scans_remaining

from . import confirmation, reset
from .permissions import REGISTRATION_REQUIRED_MESSAGE, IsRegisteredUser
from .plans import effective_plan
from .serializers import (
    ChangeEmailSerializer,
    EMAIL_IN_USE_MESSAGE,
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    UpgradeSerializer,
)
from .throttles import (
    AccountCreationThrottle,
    GuestCreationThrottle,
    PasswordResetConfirmThrottle,
    PasswordResetThrottle,
)
from .transfer import transfer_guest_scans
from .tokens import issue_tokens


User = get_user_model()

# Guests only get an access token (the frontend doesn't store a refresh token), so it has to last long enough for them to come back to their dashboard
GUEST_TOKEN_LIKETIME = timedelta(days=30)
# GUEST_TOKEN_LIFETIME is mispelled here - change if necessary but has to be across the board



# Create your views here.

class LoginView(TokenObtainPairView):
    # Same email + password sign-in as before. It also accepts an optional `guest_token` in the body and moves that guest's scans onto the account.
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]


class RegisterView(generics.CreateAPIView):
    """
    POST /api/accounts/register/   {"email", "password", "tos_agreed": true}

    Creates the account (unconfirmed) and emails the first code. The account exists even if
    that email fails: the code screen can ask for another.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AccountCreationThrottle]

    def perform_create(self, serializer):
        user = serializer.save()
        confirmation.start(user)


class TooManySessions(Throttled):
    """
    A429 with a friendly message and a code the frontend can act on.
    """

    def __init__(self, wait=None):
        super().__init__(wait=wait)
        self.detail = {
            'detail': 'Too many new sessions from your network. Try again later, or create a free account.',
            'code': 'too_many_sessions',
            'retry_after': self.wait,
        }


class GuestSessionView(APIView):
    """
    POST /api/accounts/guest/   body: {"tos_agreed": true}

    Creates a guest account and returns a long-lived access token, so a first-time visitor can run a scan and find it on their dashboard. Consent is required: without it no account is created.
    
    """
    permission_classes = [permissions.AllowAny]
    # No authentication on purpose. An old or expired token in the request header would otherwise be rejected with a 401 before this view runs.
    authentication_classes = []

    # Stops anyone creating endless guests to get around the scan allowance.
    throttle_classes = [GuestCreationThrottle]

    def throttled(self, request, wait):
        raise TooManySessions(wait=wait)

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}

        if data.get('tos_agreed') is not True:
            return Response(
                {'tos_agreed': ['You must confirm you have permission to test the target.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_guest(
            tos_agreed=True,
            tos_agreed_at=timezone.now(),
        )

        access, refresh = issue_tokens(user, access_lifetime=GUEST_TOKEN_LIKETIME)

        return Response(
            {'access': access, 'refresh': refresh, 'is_guest': True},
            status=status.HTTP_201_CREATED,
        )




class UpgradeView(APIView):
    """
    POST /api/accounts/upgrade/     header: Authorization: Bearer <guest token>
    body: {"email"}: "...", "password": "...", "tos_agreed": true}

    Turns the calling guest into a registered user. The account keeps its id, so its scans stay attached. Returns a normal login token pair.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            # Lock the row so two identical requests arriving together cannot both pass the guest check (this takes effect on Postgres).
            user = User.objects.select_for_update().get(pk=request.user.pk)

            if not user.is_guest:
                return Response(
                    {'detail': 'Only guest accounts can be upgraded.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = UpgradeSerializer(
                data=request.data,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.upgrade(user)

        # After the transaction, so the row lock isn't held while the email goes out.
        confirmation.start(user)

        # The upgrade raised the account's token version, so the guest token no
        # longer works. These are the only tokens that do.
        access, refresh = issue_tokens(user)
        return Response(
            {'access': access, 'refresh': refresh, 'is_guest': False, 'email_confirmed': False},
            status=status.HTTP_200_OK,
        )





# What PATCH /api/accounts/me/ may change. Everything else (email, plan, staff...) is ignored.
ACCOUNT_SWITCHES = ('watch_enabled', 'notifications_muted', 'email_alerts')


def me_data(user):
    plan = effective_plan(user)
    return {
        'id': user.id,
        'email': user.email,
        'is_guest': user.is_guest,
        # {"limit", "used", "remaining", "period"}, or null for accounts with no limit.
        'allowance': scans_remaining(user),
        # What the account gets right now (accounts/plans.py). watch_slots null = no limit.
        'plan': {
            'name': plan.name,
            'watch_slots': plan.watch_slots,
            'watch_cadence_days': plan.watch_cadence.days,
        },
        # Settings: murindzi on or off, the bell's mute, and murindzi's emails.
        'watch_enabled': user.watch_enabled,
        'notifications_muted': user.notifications_muted,
        'email_alerts': user.email_alerts,
        # False until the code is typed (accounts/confirmation.py); always false for guests.
        'email_confirmed': user.email_confirmed_at is not None,
        # What the code screen needs, or null once confirmed (and for guests):
        # {"confirm_by", "code_sent_at", "code_expires_at", "attempts_left", "resend_in"}
        'confirmation': confirmation.state(user),
    }


class MeView(APIView):
    """
    GET   /api/accounts/me/   the account, its allowance, its plan and its three switches.
    PATCH /api/accounts/me/   {"watch_enabled": bool, "notifications_muted": bool,
                              "email_alerts": bool}, any of them.
                              Registered accounts only. Returns the same body as GET.
    """

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsRegisteredUser()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        return Response(me_data(request.user))

    def patch(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        changes = {name: data[name] for name in ACCOUNT_SWITCHES if name in data}
        errors = {name: ['Must be true or false.'] for name, value in changes.items() if not isinstance(value, bool)}
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        for name, value in changes.items():
            setattr(user, name, value)
        if changes:
            user.save(update_fields=list(changes))
        return Response(me_data(user))


# ---------- confirming the email address (accounts/confirmation.py) ----------

def support_hint():
    address = getattr(settings, 'EMAIL_REPLY_TO', '')
    return f' If it keeps happening, write to {address}.' if address else ''


def send_problem(outcome):
    """The (status, body) to answer with when a code wasn't sent, or None if it was."""
    if outcome.status == confirmation.SENT:
        return None
    if outcome.status == confirmation.COOLDOWN:
        seconds = outcome.retry_after
        return status.HTTP_429_TOO_MANY_REQUESTS, {
            'detail': f'Wait {seconds} second{"s" if seconds != 1 else ""} before asking for another code.',
            'code': 'code_cooldown',
            'retry_after': seconds,
        }
    if outcome.status == confirmation.LIMITED:
        return status.HTTP_429_TOO_MANY_REQUESTS, {
            'detail': "That's as many codes as we can send for now. Try again tomorrow." + support_hint(),
            'code': 'code_limit',
        }
    if outcome.status == confirmation.ADDRESS_LIMIT:
        return status.HTTP_429_TOO_MANY_REQUESTS, {
            'detail': "That's as many different addresses as one account can try in a day. Try again tomorrow." + support_hint(),
            'code': 'address_limit',
        }
    if outcome.status == confirmation.ALREADY:
        return status.HTTP_400_BAD_REQUEST, {
            'detail': 'This address is already confirmed.',
            'code': 'already_confirmed',
        }
    return status.HTTP_503_SERVICE_UNAVAILABLE, {
        'detail': "We couldn't send the code just now. Try again in a few minutes." + support_hint(),
        'code': 'email_failed',
    }


class ConfirmationView(APIView):
    """Shared by the three views below: signed-in accounts only, never guests."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_guest:
            self.permission_denied(request, message=REGISTRATION_REQUIRED_MESSAGE)


class EmailCodeView(ConfirmationView):
    """
    POST /api/accounts/email/code/   (no body)

    Emails a new code to the account's address, replacing the previous one. 200 with the same
    body as GET /me/; otherwise 429 code_cooldown (with retry_after), 429 code_limit,
    503 email_failed, or 400 already_confirmed.
    """

    def post(self, request):
        problem = send_problem(confirmation.send_code(request.user))
        if problem:
            return Response(problem[1], status=problem[0])
        return Response(me_data(request.user))


class EmailConfirmView(ConfirmationView):
    """
    POST /api/accounts/email/confirm/   {"code": "123456"}

    200 with the same body as GET /me/ once confirmed (also if it already was). Otherwise 400
    with a code: code_invalid (not 6 digits, not counted as a try), code_wrong (with
    attempts_left), code_used_up (that was the last try) or code_expired (none waiting).
    """

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        outcome = confirmation.check_code(request.user, data.get('code'))

        if outcome.status in (confirmation.CONFIRMED, confirmation.ALREADY):
            return Response(me_data(request.user))
        if outcome.status == confirmation.INVALID:
            body = {'detail': 'Type the 6 digits from the email.', 'code': 'code_invalid'}
        elif outcome.status == confirmation.WRONG:
            left = outcome.attempts_left
            body = {
                'detail': f"That code isn't right. {left} {'try' if left == 1 else 'tries'} left.",
                'code': 'code_wrong',
                'attempts_left': left,
            }
        elif outcome.status == confirmation.USED_UP:
            body = {
                'detail': "That code isn't right, and it was the last try. Ask for a new code.",
                'code': 'code_used_up',
            }
        else:
            body = {'detail': 'That code has expired. Ask for a new one.', 'code': 'code_expired'}
        return Response(body, status=status.HTTP_400_BAD_REQUEST)


class EmailChangeView(ConfirmationView):
    """
    POST /api/accounts/email/change/   {"email": "...", "password": "..."}

    For an account that isn't confirmed yet: fixes its address and emails a code to the new
    one. Field errors are 400 {"email": [...]} / {"password": [...]}. Once the address has
    changed the answer is 200 with the same body as GET /me/, plus "code_sent" and, when the
    code didn't go out, "send_problem" ({"detail", "code"}).
    """
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'email_change'

    def post(self, request):
        user = request.user
        if user.email_confirmed_at is not None:
            return Response(send_problem(confirmation.Outcome(confirmation.ALREADY))[1], status=400)

        serializer = ChangeEmailSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        old_email = user.email
        try:
            outcome = confirmation.change_address(user, serializer.validated_data['email'])
        except IntegrityError:
            # Another account took the address between the check and the save.
            user.email = old_email
            return Response({'email': [EMAIL_IN_USE_MESSAGE]}, status=status.HTTP_400_BAD_REQUEST)

        if outcome.status == confirmation.ADDRESS_LIMIT:
            problem = send_problem(outcome)
            return Response(problem[1], status=problem[0])

        problem = send_problem(outcome)
        body = me_data(user)
        body['code_sent'] = problem is None
        body['send_problem'] = problem[1] if problem else None
        return Response(body)


# ---------- forgotten password (accounts/reset.py) ----------

RESET_SENT = "If an account uses this address, we've emailed it a code. It works for 15 minutes."


class PasswordResetRequestView(APIView):
    """
    POST /api/accounts/password/reset/   {"email": "..."}   (signed out)

    Emails a reset code. 200 {"detail", "resend_in"} whether or not the address has an
    account; 429 code_cooldown (with retry_after) or code_limit, 503 email_failed. Those three
    can only happen to a real account (see the note in accounts/reset.py).
    """
    permission_classes = [permissions.AllowAny]
    # A stale sign-in token in the header must never get in the way.
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        outcome = reset.request_code(serializer.validated_data["email"])
        if outcome.status in (reset.SENT, reset.NO_ACCOUNT):
            seconds = int(reset.RESEND_AFTER.total_seconds())
            return Response({"detail": RESET_SENT, "resend_in": seconds})
        if outcome.status == reset.COOLDOWN:
            problem = send_problem(confirmation.Outcome(confirmation.COOLDOWN, retry_after=outcome.retry_after))
        elif outcome.status == reset.LIMITED:
            problem = send_problem(confirmation.Outcome(confirmation.LIMITED))
        else:
            problem = send_problem(confirmation.Outcome(confirmation.FAILED))
        return Response(problem[1], status=problem[0])


class PasswordResetView(APIView):
    """
    POST /api/accounts/password/reset/confirm/
         {"email", "code", "password", "guest_token"?}   (signed out)

    Sets the new password if the code is right, signs out every other session, and signs this
    one in: 200 {"access", "refresh", "is_guest": false, "email_confirmed": true}. Otherwise
    400 {"password": [...]} (too weak; the code isn't tried), or a code problem: code_invalid,
    code_wrong (with attempts_left), code_used_up or code_expired. An address without an
    account answers code_expired.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        outcome = reset.reset_password(data["email"], data["code"], data["password"])

        if outcome.status == reset.DONE:
            user = outcome.user
            # Only now that the code proved who this is, like a correct password on sign-in.
            transfer_guest_scans(data.get("guest_token"), user)
            access, refresh = issue_tokens(user)
            return Response({"access": access, "refresh": refresh, "is_guest": False, "email_confirmed": True})

        if outcome.status == reset.INVALID:
            body = {"detail": "Type the 6 digits from the email.", "code": "code_invalid"}
        elif outcome.status == reset.WRONG:
            left = outcome.attempts_left
            body = {
                "detail": f"That code isn't right. {left} {'try' if left == 1 else 'tries'} left.",
                "code": "code_wrong",
                "attempts_left": left,
            }
        elif outcome.status == reset.USED_UP:
            body = {
                "detail": "That code isn't right, and it was the last try. Ask for a new code.",
                "code": "code_used_up",
            }
        else:
            body = {
                "detail": "That code has expired, or it isn't for this address. Ask for a new one.",
                "code": "code_expired",
            }
        return Response(body, status=status.HTTP_400_BAD_REQUEST)

