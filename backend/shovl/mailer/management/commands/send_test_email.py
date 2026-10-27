from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from mailer.services import send_email


class Command(BaseCommand):
    help = (
        "Send xikomu's test email to ADDRESS, through the same path as every other email "
        "(limits and the log included), to check that sending works. At most 5 an hour to "
        "one address."
    )

    def add_arguments(self, parser):
        parser.add_argument("address", help="Where to send the test email.")

    def handle(self, *args, **options):
        result = send_email("test", options["address"])
        row = result.record

        if not result.sent:
            detail = f" ({row.error})" if row.error else ""
            raise CommandError(f"{row.get_status_display()}{detail}.")

        if settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
            self.stdout.write(
                "Printed above instead of sent: there's no BREVO_API_KEY here, so development "
                "prints emails. Set BREVO_API_KEY to send a real one."
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Sent. Brevo message id: {row.message_id or '(none given)'}")
            )
