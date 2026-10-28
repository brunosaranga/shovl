"""
python manage.py send_launch_email            what would be sent, and to how many (sends nothing)
python manage.py send_launch_email --send     send it, up to today's email cap
python manage.py send_launch_email --send --limit 20

The launch email (mailer/templates/mailer/launch.html and .txt), once, to every CONFIRMED entry
on the launch list that hasn't had it yet. Run it again the next day for the rest if the daily
cap (EMAIL_DAILY_CAP) stopped it: it carries on where it left off and never sends twice.

Two safety catches:
- without --send it only reports;
- it refuses to send while either template still contains "DRAFT:" (write the announcement,
  then delete that line).

Every email carries a "remove me" link (and List-Unsubscribe). The daily cleanup deletes the
whole list 30 days after each entry's launch email (waitlist/services.py, KEPT_AFTER_LAUNCH).

Render's free plan has no shell: run it from your own machine with the production
DATABASE_URL, DJANGO_SECRET_KEY, BREVO_API_KEY and CORS_ALLOWED_ORIGINS set (your IP authorised
in Brevo). The secret key must be production's: the "remove me" links are signed with it, and
links signed with another key are refused by the site.
"""
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import get_template
from django.utils import timezone

from mailer.models import SentEmail
from mailer.services import send_email
from waitlist import services
from waitlist.models import WaitlistEntry

DRAFT_MARK = "DRAFT:"
FAILURES_IN_A_ROW = 5


def draft_templates():
    """The launch templates that still carry the draft line."""
    found = []
    for name in ("mailer/launch.html", "mailer/launch.txt"):
        if DRAFT_MARK in get_template(name).template.source:
            found.append(name)
    return found


class Command(BaseCommand):
    help = "Send the launch email to the confirmed launch list (reports only, unless --send)."

    def add_arguments(self, parser):
        parser.add_argument("--send", action="store_true", help="Really send. Without it, only reports.")
        parser.add_argument("--limit", type=int, default=0, help="Send at most this many in this run.")

    def handle(self, *args, **options):
        waiting = WaitlistEntry.objects.filter(confirmed_at__isnull=False, launch_sent_at__isnull=True).order_by(
            "confirmed_at", "pk"
        )
        total = waiting.count()
        pending = WaitlistEntry.objects.filter(confirmed_at__isnull=True).count()
        done = WaitlistEntry.objects.filter(launch_sent_at__isnull=False).count()
        self.stdout.write(
            f"launch list: {total} confirmed waiting, {done} already sent, {pending} unconfirmed (never emailed)"
        )

        drafts = draft_templates()
        if drafts:
            message = f"{', '.join(drafts)} still say {DRAFT_MARK!r}: write the announcement, then delete that line."
            if options["send"]:
                raise CommandError(message)
            self.stdout.write(self.style.WARNING(message))

        if not options["send"]:
            self.stdout.write("Nothing sent. Run again with --send to send.")
            return
        if options["limit"] < 0:
            raise CommandError("--limit can't be negative.")

        sent = skipped = failed = in_a_row = 0
        for entry in waiting.iterator():
            if options["limit"] and sent >= options["limit"]:
                break
            urls = services.links(entry)
            result = send_email(
                services.LAUNCH_KIND,
                entry.email,
                {"first_name": entry.first_name, "leave_url": urls["leave_url"]},
                headers={"List-Unsubscribe": f"<{urls['leave_url']}>"} if urls["leave_url"] else None,
            )
            if result.sent:
                WaitlistEntry.objects.filter(pk=entry.pk).update(launch_sent_at=timezone.now())
                sent += 1
                in_a_row = 0
                continue
            if result.status == SentEmail.STATUS_LIMITED and "daily cap" in result.record.error:
                self.stdout.write(self.style.WARNING("Today's email cap is reached: run this again tomorrow."))
                break
            if result.status in (SentEmail.STATUS_LIMITED, SentEmail.STATUS_REFUSED):
                skipped += 1  # this address already had it, or can't be emailed
                continue
            failed += 1
            in_a_row += 1
            if in_a_row >= FAILURES_IN_A_ROW:
                self.stdout.write(self.style.ERROR(f"{in_a_row} failures in a row: stopping. See admin → Email."))
                break

        left = WaitlistEntry.objects.filter(confirmed_at__isnull=False, launch_sent_at__isnull=True).count()
        self.stdout.write(f"launch email: {sent} sent, {skipped} skipped, {failed} failed, {left} still waiting")
