"""
Confirming an account's email address with a 6-digit code.

An account that signs up (or turns a guest into an account) gets a code by email straight
away and must type it before it can do anything with its own domains (accounts/permissions.py).
Accounts that existed before this get the same screen at their next visit.

The rules, all in this file:

- A code is 6 random digits, works for CODE_LIFETIME, and only for the address it was sent
  to. Only the newest code works: asking for a new one replaces the old one.
- MAX_ATTEMPTS wrong tries use a code up; then a new one has to be sent.
- One account: a new code at most every RESEND_AFTER, at most CODES_PER_DAY a day, and codes
  to at most ADDRESSES_PER_DAY different addresses a day (fixing a typo is fine, using the
  form to email strangers isn't). On top of that the mailer allows 5 codes a day to any one
  address, however many accounts ask (mailer/kinds.py).
- Codes are stored as a keyed hash, so the digits can't be read back from the database.
- Unconfirmed accounts that signed up must confirm within CONFIRM_WITHIN, or the daily
  cleanup deletes them (accounts/management/commands/purge_guests.py).

Every function returns an Outcome instead of raising, and the views turn it into an answer.
"""
import math
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from mailer.models import SentEmail
from mailer.services import address_hash, send_email

from .models import EmailCode, User

KIND = "verify_code"
CODE_DIGITS = 6
CODE_LIFETIME = timedelta(minutes=15)
MAX_ATTEMPTS = 5
RESEND_AFTER = timedelta(seconds=60)
CODES_PER_DAY = 10
ADDRESSES_PER_DAY = 3
CONFIRM_WITHIN = timedelta(days=7)
DAY = timedelta(hours=24)

# Outcome statuses
SENT = "sent"
CONFIRMED = "confirmed"
ALREADY = "already_confirmed"
COOLDOWN = "cooldown"
LIMITED = "limited"
ADDRESS_LIMIT = "address_limit"
FAILED = "failed"
WRONG = "wrong"
USED_UP = "used_up"
EXPIRED = "expired"
INVALID = "invalid"


@dataclass(frozen=True)
class Outcome:
    status: str
    retry_after: int = 0  # seconds, for COOLDOWN
    attempts_left: int = 0  # for WRONG


def needs_confirmation(user):
    """A registered account whose address isn't confirmed yet. Guests have no address."""
    return not user.is_guest and user.email_confirmed_at is None


def new_code():
    return f"{secrets.randbelow(10 ** CODE_DIGITS):0{CODE_DIGITS}d}"


def code_hash(user, code):
    return salted_hmac(
        "accounts.EmailCode.code_hash", f"{user.pk}:{code}", algorithm="sha256"
    ).hexdigest()


def clean_code(raw):
    """The digits someone typed or pasted ("123 456", "123-456"), or "" if it isn't 6 digits."""
    digits = "".join(ch for ch in str(raw or "") if not ch.isspace() and ch != "-")
    if len(digits) == CODE_DIGITS and digits.isascii() and digits.isdigit():
        return digits
    return ""


def latest_code(user):
    return EmailCode.objects.filter(user=user, purpose=EmailCode.PURPOSE_CONFIRM).first()


def usable(row, user, now):
    return (
        row is not None
        and row.expires_at > now
        and row.attempts < MAX_ATTEMPTS
        and row.sent_to == address_hash(user.email)
    )


def recent_attempts(user, now):
    """This account's code emails in the last 24 hours that were sent or tried (not refused)."""
    return SentEmail.objects.filter(
        user=user,
        kind=KIND,
        status__in=(SentEmail.STATUS_SENT, SentEmail.STATUS_FAILED),
        created_at__gte=now - DAY,
    )


def resend_in(user, now=None):
    """Seconds until this account may ask for another code (0: now)."""
    now = now or timezone.now()
    times = []
    row = latest_code(user)
    if row is not None:
        times.append(row.created_at)
    last = recent_attempts(user, now).order_by("-created_at").values_list("created_at", flat=True).first()
    if last is not None:
        times.append(last)
    if not times:
        return 0
    wait = (max(times) + RESEND_AFTER - now).total_seconds()
    return max(0, math.ceil(wait))


def state(user, now=None):
    """
    What the confirm screen needs, for /api/accounts/me/: None once confirmed (and for guests).
    """
    if not needs_confirmation(user):
        return None
    now = now or timezone.now()
    row = latest_code(user)
    active = usable(row, user, now)
    return {
        "confirm_by": user.confirm_by.isoformat() if user.confirm_by else None,
        "code_sent_at": row.created_at.isoformat() if active else None,
        "code_expires_at": row.expires_at.isoformat() if active else None,
        "attempts_left": MAX_ATTEMPTS - row.attempts if active else None,
        "resend_in": resend_in(user, now),
    }


def send_code(user, skip_cooldown=False):
    """
    Email a new code to the account's current address, replacing any earlier one.
    skip_cooldown is for a corrected address: the person shouldn't wait a minute because
    the first code went to a typo. The daily limits still apply.
    """
    if not needs_confirmation(user):
        return Outcome(ALREADY)

    now = timezone.now()
    code = new_code()
    with transaction.atomic():
        # One send at a time per account: a second request waits here, then sees the first
        # one's code and the cooldown (the lock takes effect on Postgres).
        User.objects.select_for_update().filter(pk=user.pk).first()
        if not skip_cooldown:
            wait = resend_in(user, now)
            if wait:
                return Outcome(COOLDOWN, retry_after=wait)
        if recent_attempts(user, now).count() >= CODES_PER_DAY:
            return Outcome(LIMITED)
        EmailCode.objects.filter(user=user, purpose=EmailCode.PURPOSE_CONFIRM).delete()
        row = EmailCode.objects.create(
            user=user,
            purpose=EmailCode.PURPOSE_CONFIRM,
            sent_to=address_hash(user.email),
            code_hash=code_hash(user, code),
            created_at=now,
            expires_at=now + CODE_LIFETIME,
        )

    # Outside the transaction: the row lock isn't held while Brevo answers.
    result = send_email(
        KIND,
        user.email,
        {
            "code": code,
            "minutes": int(CODE_LIFETIME.total_seconds() // 60),
            "deadline": user.confirm_by is not None,
        },
        user=user,
    )
    if result.sent:
        return Outcome(SENT)

    # Not sent: a code nobody received must not count as one waiting to be typed.
    EmailCode.objects.filter(pk=row.pk).delete()
    if result.status == SentEmail.STATUS_LIMITED:
        return Outcome(LIMITED)
    return Outcome(FAILED)


def check_code(user, raw):
    """Confirm the account's address if `raw` is its newest code."""
    if not needs_confirmation(user):
        return Outcome(ALREADY)
    code = clean_code(raw)
    if not code:
        return Outcome(INVALID)  # not counted as a try: nothing was guessed

    now = timezone.now()
    with transaction.atomic():
        row = (
            EmailCode.objects.select_for_update()
            .filter(user=user, purpose=EmailCode.PURPOSE_CONFIRM)
            .first()
        )
        if not usable(row, user, now):
            return Outcome(EXPIRED)

        if constant_time_compare(row.code_hash, code_hash(user, code)):
            User.objects.filter(pk=user.pk).update(email_confirmed_at=now, confirm_by=None)
            user.email_confirmed_at = now
            user.confirm_by = None
            EmailCode.objects.filter(user=user, purpose=EmailCode.PURPOSE_CONFIRM).delete()
            return Outcome(CONFIRMED)

        row.attempts += 1
        row.save(update_fields=["attempts"])
        left = MAX_ATTEMPTS - row.attempts
        return Outcome(WRONG, attempts_left=left) if left else Outcome(USED_UP)


def address_allowed(user, new_email, now=None):
    """
    May this account send codes to `new_email` today? At most ADDRESSES_PER_DAY different
    addresses in 24 hours; one it already used today is always fine.
    """
    now = now or timezone.now()
    used = set(recent_attempts(user, now).values_list("to_hash", flat=True))
    return address_hash(new_email) in used or len(used) < ADDRESSES_PER_DAY


def change_address(user, new_email):
    """
    Fix the address of an unconfirmed account (a typo at sign-up), then send a code to the
    new one. The caller has already checked the password, the format and that no other account
    uses the address. Raises django.db.IntegrityError if another account took it meanwhile.
    """
    if not needs_confirmation(user):
        return Outcome(ALREADY)
    if not address_allowed(user, new_email):
        return Outcome(ADDRESS_LIMIT)

    with transaction.atomic():
        user.email = new_email
        user.save(update_fields=["email"])
        EmailCode.objects.filter(user=user, purpose=EmailCode.PURPOSE_CONFIRM).delete()
    return send_code(user, skip_cooldown=True)


def start(user):
    """
    Right after sign-up or an upgrade: the account has CONFIRM_WITHIN to confirm, and the first
    code goes out. Never raises; an unsent code can be asked for again on the confirm screen.
    """
    if not needs_confirmation(user):
        return Outcome(ALREADY)
    if user.confirm_by is None:
        user.confirm_by = timezone.now() + CONFIRM_WITHIN
        user.save(update_fields=["confirm_by"])
    return send_code(user)
