"""
python manage.py run_watches [--budget SECONDS] [--dry-run]

Runs the scheduled scans that are due (watch/runner.py). On Render this
is the cron job, every 15 minutes. Each line names a watch by its id
and host + path only: query strings can hold API keys, and these lines
end up in the host's logs.
"""
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from watch import runner
from watch.models import Watch


def where(watch):
    parts = urlsplit(watch.target_url)
    return f"{parts.hostname}{parts.path or '/'}"


def describe(outcome):
    name = f"watch {outcome.watch.pk} {where(outcome.watch)}"
    if outcome.result == "complete":
        risk = outcome.scan.risk_score or "no score"
        worse = ", got worse" if outcome.worse else ""
        return f"{name}: complete, risk {risk}{worse}"
    if outcome.result == "failed":
        return f"{name}: failed ({outcome.reason}), retry in 1 hour"
    if outcome.result == "unverified":
        tries = outcome.watch.verification_failures
        return (
            f"{name}: verification failed ({tries} of "
            f"{Watch.MAX_FAILURES}), retry in 1 hour"
        )
    if outcome.result == "paused":
        if outcome.reason == "verification":
            return f"{name}: paused, domain back to pending"
        return f"{name}: paused after {Watch.MAX_FAILURES} failed runs"
    return f"{name}: skipped, it changed during the pass"


class Command(BaseCommand):
    help = "shovl watch: run the scheduled scans that are due."

    def add_arguments(self, parser):
        parser.add_argument(
            "--budget",
            type=int,
            default=runner.BUDGET_SECONDS,
            help="Seconds before it stops picking up new watches (600).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the watches that are due, without scanning.",
        )

    def handle(self, *args, **options):
        if options["budget"] < 1:
            raise CommandError("--budget must be at least 1.")

        if options["dry_run"]:
            due = runner.due_watches(timezone.now())
            self.stdout.write(f"{len(due)} watch(es) due")
            for watch in due:
                when = watch.next_run_at.strftime("%Y-%m-%d %H:%M")
                self.stdout.write(
                    f"  watch {watch.pk} {where(watch)}, due {when} UTC"
                )
            return

        summary = runner.run_pass(budget_seconds=options["budget"])
        for outcome in summary.outcomes:
            self.stdout.write(describe(outcome))
        self.stdout.write(
            f"run_watches: {summary.due} due, "
            f"{summary.count('complete')} complete "
            f"({sum(o.worse for o in summary.outcomes)} worse), "
            f"{summary.count('failed')} failed, "
            f"{summary.count('unverified')} unverified, "
            f"{summary.count('paused')} paused, "
            f"{summary.left} left for the next run, "
            f"{summary.stale} stale scan(s) tidied"
        )
