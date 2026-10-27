"""
Sending email: send_email(kind, to, context=None, user=None) returns a SendResult.

Every email xikomu sends goes through here, and in this order:

1. The kind must be listed in mailer/kinds.py (subject, templates, per-address limit).
2. Addresses that must never be emailed are refused: guest accounts, the guests' ".invalid"
   placeholders, and anything that isn't a valid address.
3. A server without a Brevo key (production) sends nothing: "disabled".
4. Limits: the kind's own limit per address, and EMAIL_DAILY_CAP across everything, which keeps
   xikomu under Brevo's free 300 a day with room left for replies sent from Gmail.
5. The templates are rendered and the email goes to Brevo over HTTPS (django-anymail; Render's
   free plan blocks the SMTP ports).

It never raises because of a delivery problem: the caller gets a SendResult and decides what to
tell the person. Every attempt, sent or not, is recorded as a SentEmail, without the address
itself (only a keyed hash of it), and the address is kept out of the logs and the stored error.
"""
import logging
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .kinds import KINDS
from .models import SentEmail

logger = logging.getLogger("mailer")

DAY = timedelta(hours=24)
ERROR_MAX = 300

# What Brevo can answer for a message it won't deliver (anymail's normalised statuses).
UNDELIVERABLE = {"rejected", "failed", "invalid"}


@dataclass(frozen=True)
class SendResult:
    status: str
    record: SentEmail

    @property
    def sent(self):
        return self.status == SentEmail.STATUS_SENT


def normalize(address):
    """Trimmed and lowercased, the same way accounts store addresses (accounts/models.py)."""
    return (address or "").strip().lower()


def address_hash(address):
    """
    A keyed hash of the address. The same address always gives the same value, so the limits
    can count what went to it; without the server's secret key it can't be reversed by trying
    addresses.
    """
    return salted_hmac(
        "mailer.SentEmail.to_hash", normalize(address), algorithm="sha256"
    ).hexdigest()


def refusal_reason(address, user=None):
    """Why this address must not be emailed, or "" if it may."""
    if user is not None and getattr(user, "is_guest", False):
        return "guest account"
    try:
        validate_email(address)
    except ValidationError:
        return "not a valid address"
    domain = address.rsplit("@", 1)[-1]
    # ".invalid" is reserved and can never receive mail: the guests' placeholder addresses
    # (accounts/models.py, GUEST_EMAIL_DOMAIN) end in it.
    if domain == "invalid" or domain.endswith(".invalid"):
        return "reserved .invalid address"
    return ""


def limit_reason(kind, to_hash, now=None):
    """Why sending now would break a limit, or "" if it wouldn't."""
    now = now or timezone.now()
    recent = SentEmail.objects.filter(
        kind=kind.name,
        to_hash=to_hash,
        status__in=(SentEmail.STATUS_SENT, SentEmail.STATUS_FAILED),
        created_at__gte=now - kind.window,
    ).count()
    if recent >= kind.per_address:
        return "too many of this kind to this address"
    sent_lately = SentEmail.objects.filter(
        status=SentEmail.STATUS_SENT, created_at__gte=now - DAY
    ).count()
    if sent_lately >= settings.EMAIL_DAILY_CAP:
        return "daily cap reached"
    return ""


def provider_message_id(message):
    """Brevo's id for the message, once anymail has sent it ("" before that, or if none)."""
    status = getattr(message, "anymail_status", None)
    message_id = getattr(status, "message_id", None)
    if message_id is None:
        return ""
    if isinstance(message_id, set):  # several recipients: one id each
        return ",".join(sorted(str(i) for i in message_id))
    return str(message_id)


def base_context():
    """What every template can use. The site is the frontend's address, as in the PDF footer."""
    origins = list(getattr(settings, "CORS_ALLOWED_ORIGINS", []) or [])
    site_url = origins[0] if origins else ""
    return {
        "brand": "xikomu",
        "site_url": site_url,
        "site_host": urlsplit(site_url).hostname or "",
        "support_email": settings.EMAIL_REPLY_TO,
    }


def send_email(kind, to, context=None, user=None):
    kind = KINDS[kind]  # an unknown kind is a programming error, not a delivery problem
    address = normalize(to)
    to_hash = address_hash(address)
    owner = user if user is not None and user.pk else None

    def record(status, message_id="", error=""):
        row = SentEmail.objects.create(
            kind=kind.name,
            user=owner,
            to_hash=to_hash,
            status=status,
            message_id=message_id[:200],
            error=error[:ERROR_MAX],
        )
        return SendResult(status, row)

    reason = refusal_reason(address, user)
    if reason:
        return record(SentEmail.STATUS_REFUSED, error=reason)

    if not settings.MAILER_ENABLED:
        logger.warning("email %s not sent: no BREVO_API_KEY on this server", kind.name)
        return record(SentEmail.STATUS_DISABLED)

    reason = limit_reason(kind, to_hash)
    if reason:
        logger.warning("email %s to %s… not sent: %s", kind.name, to_hash[:8], reason)
        return record(SentEmail.STATUS_LIMITED, error=reason)

    # Rendering errors are bugs (a missing template, a typo), so they are not caught here:
    # the tests render every kind.
    values = {**base_context(), **(context or {})}
    # Only the kind's own {placeholders} are filled (mailer/kinds.py): server-made values.
    subject = kind.subject.format_map(values)
    values["subject"] = subject
    text = render_to_string(f"mailer/{kind.template}.txt", values)
    html = render_to_string(f"mailer/{kind.template}.html", values)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[address],
        reply_to=[settings.EMAIL_REPLY_TO] if settings.EMAIL_REPLY_TO else None,
    )
    message.attach_alternative(html, "text/html")
    message.tags = [kind.name]  # shown in Brevo's logs; other backends ignore it

    try:
        message.send()
    except Exception as exc:  # anymail's API and network errors, or anything else on the way
        # (including anymail refusing to go on when Brevo rejects the only recipient).
        # anymail's messages can quote the recipient: keep the address out of what's stored.
        error = f"{type(exc).__name__}: {exc}".replace(address, "<recipient>")
        logger.warning("email %s to %s… failed: %s", kind.name, to_hash[:8], error[:ERROR_MAX])
        return record(SentEmail.STATUS_FAILED, message_id=provider_message_id(message), error=error)

    status = getattr(message, "anymail_status", None)
    message_id = provider_message_id(message)
    if status is not None and set(status.status or ()) & UNDELIVERABLE:
        error = f"Brevo answered {', '.join(sorted(status.status))}"
        logger.warning("email %s to %s… refused by Brevo: %s", kind.name, to_hash[:8], error)
        return record(SentEmail.STATUS_FAILED, message_id=message_id, error=error)

    return record(SentEmail.STATUS_SENT, message_id=message_id)
