"""
Every kind of email xikomu can send, in one place: its subject, its templates and how often
one address may receive it. mailer/services.py refuses any kind that isn't listed here, so
nothing can be emailed by accident.

The templates are mailer/templates/mailer/<template>.html and <template>.txt (both are sent:
the text part for clients that don't show HTML). Subjects are fixed text, never anything a
visitor typed.

Kinds still to come, each with its own step: verify_code (email verification), watch_alert
(murindzi), password_reset, waitlist_confirm and launch (the launch waitlist).
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
    ]
}
