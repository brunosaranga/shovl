"""
Resetting a forgotten password with a 6-digit code emailed to the account's address.

    request_code(email)                       email a code, if the address has an account
    reset_password(email, code, new_password) check the code, set the password

The code works like the confirmation code (accounts/confirmation.py): 6 random digits, valid
for CODE_LIFETIME, only for the address it was sent to, only the newest one, MAX_ATTEMPTS
wrong tries use it up, stored as a keyed hash. Reset codes and confirmation codes are separate
rows with separate hashes, so one can never stand in for the other.

When the code is right:
- the new password is set, and the account's token version goes up, which signs out every
  session it had (accounts/tokens.py): whoever knew the old password is out;
- the address counts as confirmed, because typing the code proves it is the owner's (an
  unconfirmed sign-up that forgot its password needs nothing else, and someone who signed up
  with an address that isn't theirs loses the account to its real owner);
- every reset and confirmation code of the account is deleted.

Limits: one account gets a new code at most every RESEND_AFTER and CODES_PER_DAY a day; the
mailer allows 5 reset emails a day to one address (mailer/kinds.py); the two endpoints are
also limited per network (accounts/throttles.py).

About telling who has an account: an address with no account gets the same answer as one that
has (the view words it "if an account uses this address"). The sign-up form already says when
an address is taken, so this isn't a secret xikomu keeps; the waits and limits below can only
happen to a real account and are reported honestly, so nobody waits for an email that isn't
coming.
"""
import math
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from mailer.models import SentEmail
from mailer.services import address_hash, send_email

from .confirmation import clean_code, code_hash, new_code, usable
from .models import EmailCode

User = get_user_model()

KIND = "password_reset"
PURPOSE = EmailCode.PURPOSE_RESET
CODE_LIFETIME = timedelta(minutes=15)
MAX_ATTEMPTS = 5
RESEND_AFTER = timedelta(seconds=60)
CODES_PER_DAY = 10
DAY = timedelta(hours=24)

# Outcome statuses
SENT = "sent"
NO_ACCOUNT = "no_account"
COOLDOWN = "cooldown"
LIMITED = "limited"
FAILED = "failed"
DONE = "done"
INVALID = "invalid"
WRONG = "wrong"
USED_UP = "used_up"
EXPIRED = "expired"


@dataclass(frozen=True)
class Outcome:
    status: str
    retry_after: int = 0
    attempts_left: int = 0
    user: object = None


def account_for(email):
    """The account that may reset its password with this address, or None."""
    address = User.objects.normalize_email(email)
    if not address:
        return None
    return User.objects.filter(email__iexact=address, is_guest=False, is_active=True).first()


def _latest(user):
    return EmailCode.objects.filter(user=user, purpose=PURPOSE).first()


def _recent_attempts(user, now):
    return SentEmail.objects.filter(
        user=user,
        kind=KIND,
        status__in=(SentEmail.STATUS_SENT, SentEmail.STATUS_FAILED),
        created_at__gte=now - DAY,
    )


def _resend_in(user, now):
    times = []
    row = _latest(user)
    if row is not None:
        times.append(row.created_at)
    last = _recent_attempts(user, now).order_by("-created_at").values_list("created_at", flat=True).first()
    if last is not None:
        times.append(last)
    if not times:
        return 0
    return max(0, math.ceil((max(times) + RESEND_AFTER - now).total_seconds()))


def request_code(email):
    """Email a reset code to the account using this address, replacing any earlier one."""
    user = account_for(email)
    if user is None:
        return Outcome(NO_ACCOUNT)

    now = timezone.now()
    code = new_code()
    with transaction.atomic():
        # One request at a time per account (the lock takes effect on Postgres).
        User.objects.select_for_update().filter(pk=user.pk).first()
        wait = _resend_in(user, now)
        if wait:
            return Outcome(COOLDOWN, retry_after=wait)
        if _recent_attempts(user, now).count() >= CODES_PER_DAY:
            return Outcome(LIMITED)
        EmailCode.objects.filter(user=user, purpose=PURPOSE).delete()
        row = EmailCode.objects.create(
            user=user,
            purpose=PURPOSE,
            sent_to=address_hash(user.email),
            code_hash=code_hash(user, code, PURPOSE),
            created_at=now,
            expires_at=now + CODE_LIFETIME,
        )

    result = send_email(
        KIND,
        user.email,
        {"code": code, "minutes": int(CODE_LIFETIME.total_seconds() // 60)},
        user=user,
    )
    if result.sent:
        return Outcome(SENT)
    # Not sent: a code nobody received must not be waiting to be typed.
    EmailCode.objects.filter(pk=row.pk).delete()
    if result.status == SentEmail.STATUS_LIMITED:
        return Outcome(LIMITED)
    return Outcome(FAILED)


def reset_password(email, raw_code, new_password):
    """
    Set a new password if `raw_code` is the newest reset code of the account using `email`.
    The caller has already checked the new password's strength. An address without an
    account answers EXPIRED, exactly like a code that ran out.
    """
    code = clean_code(raw_code)
    if not code:
        return Outcome(INVALID)  # not counted as a try: nothing was guessed
    user = account_for(email)
    if user is None:
        return Outcome(EXPIRED)

    now = timezone.now()
    with transaction.atomic():
        row = EmailCode.objects.select_for_update().filter(user=user, purpose=PURPOSE).first()
        if not usable(row, user, now):
            return Outcome(EXPIRED)
        if not constant_time_compare(row.code_hash, code_hash(user, code, PURPOSE)):
            row.attempts += 1
            row.save(update_fields=["attempts"])
            left = MAX_ATTEMPTS - row.attempts
            return Outcome(WRONG, attempts_left=left) if left else Outcome(USED_UP)

        user = User.objects.select_for_update().get(pk=user.pk)
        user.set_password(new_password)
        # Signs out every session the account had (accounts/tokens.py).
        user.token_version += 1
        fields = ["password", "token_version"]
        if user.email_confirmed_at is None:
            user.email_confirmed_at = now
            user.confirm_by = None
            fields += ["email_confirmed_at", "confirm_by"]
        user.save(update_fields=fields)
        EmailCode.objects.filter(user=user).delete()

    # A reset proves the address too: a box ticked at sign-up now counts (waitlist/).
    from waitlist.services import account_confirmed

    account_confirmed(user)
    return Outcome(DONE, user=user)
