"""
Every kind of email xikomu can send, in one place: its subject, its templates and how often
one address may receive it. mailer/services.py refuses any kind that isn't listed here, so
nothing can be emailed by accident.

The templates are mailer/templates/mailer/<template>.html and <template>.txt (both are sent:
the text part for clients that don't show HTML). A subject is fixed text, or names a value
the server made itself in {braces}, such as the {code} it generated: never anything a visitor
typed.

Kinds still to come, each with its own step: watch_alert (murindzi), password_reset,
waitlist_confirm and launch (the launch waitlist).
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
    ]
}
