"""
Every kind of email xikomu can send, in one place: its subject, its templates and how often
one address may receive it. mailer/services.py refuses any kind that isn't listed here, so
nothing can be emailed by accident.

The templates are mailer/templates/mailer/<template>.html and <template>.txt (both are sent:
the text part for clients that don't show HTML). A subject is fixed text, or fills {braces}
with a value the server made itself (the {code} it generated, a headline it wrote from the
recipient's own watched APIs): never text someone else typed.

Kinds still to come: waitlist_confirm and launch (the launch waitlist).
"""
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Kind:
    name: str
    subject: str
    template: str
    # At most `per_address` emails of this kind to one address within `window`. Sent and
    # failed attempts both count, so a failing send can't be retried in a tight loop.
    per_address: int
    window: timedelta


KINDS = {
    kind.name: kind
    for kind in [
        # python manage.py send_test_email you@example.com: checks that sending works.
        Kind(
            name="test",
            subject="xikomu: test email",
            template="test",
            per_address=5,
            window=timedelta(hours=1),
        ),
        # The 6-digit code that confirms an address (accounts/confirmation.py). The code is in
        # the subject so it can be read from the notification. Five a day to one address,
        # however many accounts ask: someone signing up with a stranger's address can't fill
        # their inbox.
        Kind(
            name="verify_code",
            subject="xikomu: your code is {code}",
            template="verify_code",
            per_address=5,
            window=timedelta(hours=24),
        ),
        # A forgotten password (accounts/reset.py). Unlike the confirmation code, the code is
        # NOT in the subject: subjects show on lock screens, and this one changes a password.
        Kind(
            name="password_reset",
            subject="xikomu: reset your password",
            template="password_reset",
            per_address=5,
            window=timedelta(hours=24),
        ),
        # murindzi's alerts: one email per account per runner pass, listing every watched API
        # that got worse or was paused in it (notifications/emails.py). The runner passes
        # hourly, so a bad day could mean many; at most 10 a day to one address.
        Kind(
            name="watch_alert",
            subject="xikomu: {headline}",
            template="watch_alert",
            per_address=10,
            window=timedelta(hours=24),
        ),
    ]
}
