"""
The launch list: people who asked to hear, once, when xikomu officially launches.

    join(email, first_name, source, ...)   a request (the modal, or the tick at sign-up)
    confirm(token)                         the confirmation email's button
    leave(token)                           "remove me", from any of the list's emails
    account_confirmed(user)                the sign-up tick, once the account's code is typed

Double opt-in: a request is only a *pending* entry. It's confirmed by a click on the button in
the confirmation email, or, for the tick at sign-up, by the account's own confirmation code
(the tick is the consent, the code proves the address is theirs). Only confirmed entries ever
get the launch email (waitlist/management/commands/send_launch_email.py).

Safeguards:
- The confirmation email contains nothing anyone typed: no name, no echo. The name is only
  used after confirmation, and only if it passes NAME_RE (letters in any language, spaces,
  hyphens, apostrophes; no digits, @ or links), at most NAME_MAX characters.
- The same answer whatever the address (new, pending, already on the list): the views never
  say which. A filled honeypot field is answered the same way and does nothing.
- At most one confirmation email per address per day and CONFIRM_EMAILS_MAX in total, so the
  form can't fill a stranger's inbox; the mailer allows one a day too (mailer/kinds.py).
- Confirmation links: a long random token, single use, CONFIRM_LINK_LIFETIME, stored only as a
  SHA-256 digest. Leave links are signed with the server's secret key.
- Confirming or leaving needs a button press (POST) on our page: mail scanners open links.
"""
import hashlib
import logging
import re
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone

from mailer.services import address_hash, base_context, send_email

from .models import WaitlistEntry

# The promise people agree to. Shown word for word next to the button (frontend
# content/en/waitlist.js) and stored with every entry. Change the wording? Bump the version,
# here and in the frontend together.
CONSENT_VERSION = "2026-10-28"
CONSENT_TEXT = (
    "Email me once when xikomu officially launches. Nothing else, and I can remove myself any time."
)

NAME_MAX = 50
# Letters (any language), joined by single spaces, hyphens or apostrophes.
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ '\-’][^\W\d_]+)*$")

CONFIRM_LINK_LIFETIME = timedelta(hours=48)
CONFIRM_EMAIL_EVERY = timedelta(hours=24)
CONFIRM_EMAILS_MAX = 3
PENDING_KEPT = timedelta(days=7)
KEPT_AFTER_LAUNCH = timedelta(days=30)

logger = logging.getLogger("waitlist")

CONFIRM_KIND = "waitlist_confirm"
LAUNCH_KIND = "launch"
LEAVE_SALT = "waitlist.leave"


def normalize_email(email):
    return (email or "").strip().lower()


def clean_name(raw):
    """The first name, tidied, or None if it isn't one."""
    name = " ".join(str(raw or "").split())
    if not name or len(name) > NAME_MAX or not NAME_RE.match(name):
        return None
    return name


def _digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def leave_token(entry):
    return signing.dumps({"e": entry.pk, "h": address_hash(entry.email)[:16]}, salt=LEAVE_SALT, compress=True)


def links(entry, confirm_token=None):
    """The page addresses on the site for this entry's emails ("" without a site address)."""
    site = base_context()["site_url"]
    if not site:
        return {"confirm_url": "", "leave_url": ""}
    return {
        "confirm_url": f"{site}/waitlist/confirm?t={quote(confirm_token)}" if confirm_token else "",
        "leave_url": f"{site}/waitlist/leave?t={quote(leave_token(entry))}",
    }


def _send_confirmation(entry, now):
    """A new confirmation link, if this address may get another email. Never raises."""
    if entry.confirm_emails_sent >= CONFIRM_EMAILS_MAX:
        return False
    if entry.last_confirm_email_at and entry.last_confirm_email_at > now - CONFIRM_EMAIL_EVERY:
        return False
    token = secrets.token_urlsafe(32)
    WaitlistEntry.objects.filter(pk=entry.pk).update(
        token_hash=_digest(token),
        token_expires_at=now + CONFIRM_LINK_LIFETIME,
        confirm_emails_sent=entry.confirm_emails_sent + 1,
        last_confirm_email_at=now,
    )
    entry.refresh_from_db()
    urls = links(entry, token)
    result = send_email(
        CONFIRM_KIND,
        entry.email,
        {"confirm_url": urls["confirm_url"], "leave_url": urls["leave_url"], "hours": 48},
        headers={"List-Unsubscribe": f"<{urls['leave_url']}>"} if urls["leave_url"] else None,
    )
    return result.sent


def join(email, first_name, source, account=None, signed_in=None):
    """
    A request to join. Returns "confirmed" only when `signed_in` is a confirmed account asking
    with its own address (it's on the list at once); otherwise "pending", whatever happened, so
    the reply never says whether the address was new, pending or already on the list.
    Raises ValueError for a missing or invalid name or address (a field error, not a secret).
    """
    address = normalize_email(email)
    if not address or "@" not in address:
        raise ValueError("email")
    name = ""
    if first_name is not None and str(first_name).strip():
        name = clean_name(first_name)
        if name is None:
            raise ValueError("first_name")
    elif source == WaitlistEntry.SOURCE_AFTER_SCAN:
        raise ValueError("first_name")

    now = timezone.now()
    own_address = (
        signed_in is not None
        and not signed_in.is_guest
        and signed_in.email_confirmed_at is not None
        and signed_in.email == address
    )

    with transaction.atomic():
        entry = WaitlistEntry.objects.select_for_update().filter(email=address).first()
        if entry is not None and entry.confirmed:
            return "confirmed" if own_address else "pending"
        fields = {
            "first_name": name,
            "source": source,
            "account": account,
            "consent_version": CONSENT_VERSION,
            "consent_text": CONSENT_TEXT,
            "agreed_at": now,
        }
        if own_address:
            fields["confirmed_at"] = now
            fields["token_hash"] = ""
            fields["token_expires_at"] = None
        if entry is None:
            try:
                with transaction.atomic():
                    entry = WaitlistEntry.objects.create(email=address, **fields)
            except IntegrityError:
                return "pending"  # the same address, a moment earlier
        else:
            for key, value in fields.items():
                setattr(entry, key, value)
            entry.save()

    if own_address:
        return "confirmed"
    if source == WaitlistEntry.SOURCE_REGISTRATION:
        return "pending"  # the account's own code confirms it (account_confirmed)
    _send_confirmation(entry, now)
    return "pending"


def confirm(token):
    """The confirmation button. The entry, now confirmed, or None if the link isn't (still) good."""
    if not token:
        return None
    now = timezone.now()
    with transaction.atomic():
        entry = (
            WaitlistEntry.objects.select_for_update()
            .filter(token_hash=_digest(str(token)), token_expires_at__gt=now, confirmed_at__isnull=True)
            .first()
        )
        if entry is None:
            return None
        entry.confirmed_at = now
        entry.token_hash = ""  # single use
        entry.token_expires_at = None
        entry.save(update_fields=["confirmed_at", "token_hash", "token_expires_at"])
    return entry


def leave(token):
    """ "remove me": deletes the entry. True if the link was genuine (even if already gone)."""
    try:
        data = signing.loads(str(token or ""), salt=LEAVE_SALT)
        pk, check = int(data["e"]), str(data["h"])
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        return False
    entry = WaitlistEntry.objects.filter(pk=pk).first()
    if entry is not None and address_hash(entry.email)[:16] == check:
        entry.delete()
    return True


def account_confirmed(user):
    """
    The account just proved its address (its code, or a password reset): the box it ticked at
    sign-up now counts, for the address it proved. If the address was corrected after the tick
    (a typo fixed on the code screen), the entry moves to the proven address; if that address is
    already on the list, the old entry just goes. Only this account's own tick counts: an entry
    left behind by a deleted account isn't picked up by a new one with the same address.
    Never raises: joining the list must not get in the way of confirming.
    """
    try:
        address = normalize_email(user.email)
        now = timezone.now()
        with transaction.atomic():
            ticked = WaitlistEntry.objects.select_for_update().filter(
                account=user, source=WaitlistEntry.SOURCE_REGISTRATION, confirmed_at__isnull=True
            )
            for entry in ticked:
                if entry.email != address:
                    if WaitlistEntry.objects.filter(email=address).exists():
                        entry.delete()
                        continue
                    entry.email = address
                entry.confirmed_at = now
                entry.save(update_fields=["email", "confirmed_at"])
    except Exception:
        logger.exception("Couldn't confirm the launch list entry of account %s", user.pk)


def expired(now=None):
    """What the daily cleanup deletes: pending past PENDING_KEPT, everyone KEPT_AFTER_LAUNCH after the launch email."""
    now = now or timezone.now()
    pending = WaitlistEntry.objects.filter(confirmed_at__isnull=True, created_at__lt=now - PENDING_KEPT)
    launched = WaitlistEntry.objects.filter(launch_sent_at__lt=now - KEPT_AFTER_LAUNCH)
    return pending, launched
