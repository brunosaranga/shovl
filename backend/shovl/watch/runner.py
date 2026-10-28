"""
murindzi's runner: one pass over the watches that are due.
The run_watches command (Render's cron job) calls run_pass().

One pass:
  1. Scheduled scans left "running" by a killed run become interrupted.
  2. Watches booked further ahead than their plan now allows come
     forward (a shorter free cadence, an upgrade to Pro; see pull_in).
  3. Due watches are picked, most overdue first (see due_watches).
  4. One at a time, until the time budget is spent:
       claim     next run an hour ahead, a failure counted up front
       re-check  the domain's verification, once per domain per pass
       scan      same engine as the dashboard, writes off
       book      success: failures back to 0, next run in its slot
                 failure: tried again in an hour
  5. Watches left over are still due and go first next pass.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from accounts.plans import effective_plan, free_plan, pro_plan
from domains.verification import verify_dns, verify_file
from scanner.engine import ScanFailed, run_scan
from scanner.report import format_report
from scans.compare import RANK, comparison_for
from scans.models import ACTIVE_STATUSES, TRIGGER_WATCH, Scan

from notifications.emails import EmailTally, send_watch_emails
from notifications.services import record_outcome

from . import services
from .models import Watch

logger = logging.getLogger(__name__)

# Stop picking up new watches after this long. The scan in flight
# always finishes (a scan is capped at 90 seconds by the scanner).
BUDGET_SECONDS = 600
# A failed run, or a run that died half way, is tried again this later.
RETRY_DELAY = timedelta(hours=1)
# A scheduled scan still running after this long was left behind.
STALE_AFTER = timedelta(minutes=15)

SCAN_ERROR = "The scan hit an unexpected problem."


@dataclass
class Outcome:
    """What happened to one watch in a pass."""

    watch: Watch
    # complete | failed | unverified | paused | skipped
    result: str
    reason: str = ""
    scan: Scan | None = None
    comparison: dict | None = None
    worse: bool = False


@dataclass
class PassSummary:
    due: int = 0
    left: int = 0
    stale: int = 0
    pulled: int = 0
    outcomes: list = field(default_factory=list)
    # murindzi's alert emails, sent once the pass is over (notifications/emails.py).
    emails: EmailTally = field(default_factory=EmailTally)

    def count(self, result):
        return sum(1 for o in self.outcomes if o.result == result)


# ---------- picking ----------------------------------------------------

def sweep_stale_scans(now):
    """Scheduled scans a killed run left 'running'. Returns how many."""
    return Scan.objects.filter(
        trigger=TRIGGER_WATCH,
        status__in=ACTIVE_STATUSES,
        created_at__lt=now - STALE_AFTER,
    ).update(status="interrupted")


def due_watches(now):
    """
    The watches that may run now, most overdue first: active, not
    paused, the account active with its switch on, next run passed,
    and within the plan's slots (worked out per account, once).
    """
    candidates = (
        Watch.objects.filter(
            active=True,
            paused_reason="",
            next_run_at__lte=now,
            user__is_active=True,
            user__watch_enabled=True,
        )
        .select_related("user", "domain")
        .order_by("next_run_at", "pk")
    )
    in_plan = {}
    due = []
    for watch in candidates:
        if watch.user_id not in in_plan:
            in_plan[watch.user_id] = services.in_plan_ids(watch.user)
        if watch.pk in in_plan[watch.user_id]:
            due.append(watch)
    return due


def pull_in(now, dry_run=False):
    """
    Watches booked further ahead than their plan allows now come
    forward. That happens when the free plan's cadence gets shorter
    (WATCH_FREE_CADENCE_DAYS=7 for the beta) or an account moves to
    Pro: a watch booked 30 days out would otherwise wait the 30 days.

    Only a watch due more than one cadence (plus the spread) from now
    moves, so a retry an hour out is never touched. It moves to one
    cadence after its last scheduled scan (or its start), plus the
    usual spread, or to now when that's already past: always earlier,
    never later. Returns the watches moved (dry_run: that would move).
    """
    shortest = min(free_plan().watch_cadence, pro_plan().watch_cadence)
    candidates = Watch.objects.filter(
        active=True,
        paused_reason="",
        next_run_at__gt=now + shortest + services.SPREAD,
    ).select_related("user")
    plans = {}
    moved = []
    for watch in candidates:
        if watch.user_id not in plans:
            plans[watch.user_id] = effective_plan(watch.user)
        plan = plans[watch.user_id]
        if watch.next_run_at <= now + plan.watch_cadence + services.SPREAD:
            continue
        base = watch.last_run_at or watch.activated_at
        when = max(services.next_run_from(base, plan), now)
        if not dry_run:
            # Conditional, like claim(): a watch changed since it was
            # read (turned back on, say) keeps its new booking.
            changed = Watch.objects.filter(
                pk=watch.pk, next_run_at=watch.next_run_at,
            ).update(next_run_at=when)
            if not changed:
                continue
        watch.next_run_at = when
        moved.append(watch)
    return moved


def claim(watch, now):
    """
    Take the watch for this run: next run an hour ahead and a failure
    counted up front, in one conditional update. A run that dies half
    way leaves a counted failure, retried in an hour, never a loop.
    False when the watch changed since it was read.
    """
    taken = Watch.objects.filter(
        pk=watch.pk,
        next_run_at=watch.next_run_at,
        active=True,
        paused_reason="",
    ).update(
        next_run_at=now + RETRY_DELAY,
        consecutive_failures=F("consecutive_failures") + 1,
    )
    if taken:
        watch.refresh_from_db()
    return bool(taken)


# ---------- the domain -------------------------------------------------

def still_verified(domain, checked):
    """
    The live re-check (DNS record or file), once per domain per pass:
    `checked` remembers the answers. The verify functions never raise.
    """
    if domain.pk not in checked:
        if domain.verification_method == "file":
            verify = verify_file
        else:
            verify = verify_dns
        ok = verify(domain.hostname, domain.verification_token)
        checked[domain.pk] = bool(ok)
    return checked[domain.pk]


def _verification_failed(watch, now):
    watch.verification_failures += 1
    watch.last_error = "verification"
    watch.save(update_fields=["verification_failures", "last_error"])
    if watch.verification_failures >= Watch.MAX_FAILURES:
        # Rule A: domain back to pending, every watch on it paused.
        services.domain_lost_verification(watch.domain, now)
        watch.refresh_from_db()
        return Outcome(watch, "paused", reason="verification")
    return Outcome(watch, "unverified", reason="verification")


def _verification_passed(watch):
    if watch.verification_failures:
        watch.verification_failures = 0
        watch.save(update_fields=["verification_failures"])
    domain = watch.domain
    if not domain.verified:
        # Pending (it lost verification earlier) but the record is
        # back: verified again, and its other paused watches restart.
        domain.verified = True
        domain.verified_at = timezone.now()
        domain.save(update_fields=["verified", "verified_at"])
        services.domain_verified_again(domain)


# ---------- the scan ---------------------------------------------------

def _finish(scan, status, **fields):
    """Save the end of a scan, unless someone stopped it first."""
    saved = Scan.objects.filter(
        pk=scan.pk, status__in=ACTIVE_STATUSES
    ).update(status=status, completed_at=timezone.now(), **fields)
    scan.refresh_from_db()
    return bool(saved)


def _failed(scan, reason, message):
    error = {"error": {"reason": reason, "message": message}}
    _finish(scan, "failed", results=error)
    return reason


def scan_now(watch):
    """
    One scheduled scan of the watch's API: the dashboard's engine,
    writes off (no mass assignment POST), "suggest fix" on, verbose
    off, saved with trigger "watch". Returns (scan, reason), where
    reason is empty when the scan completed.
    """
    scan = Scan.objects.create(
        user=watch.user,
        target_url=watch.target_url,
        status="running",
        verbose=False,
        suggest_fix=True,
        trigger=TRIGGER_WATCH,
    )
    try:
        raw = run_scan(
            watch.target_url,
            verbose=False,
            suggest_fix=True,
            generate_report=True,
            allow_writes=False,
        )
        report = format_report(raw)
    except ScanFailed as e:
        return scan, _failed(scan, e.reason, e.message)
    except Exception:
        logger.exception("Scheduled scan %s crashed", scan.pk)
        return scan, _failed(scan, "scan_error", SCAN_ERROR)

    saved = _finish(
        scan,
        "complete",
        risk_score=report["meta"]["risk_score"],
        results=report,
    )
    return scan, "" if saved else "stopped"


def got_worse(comparison):
    """A new problem, a check that got worse, or a higher risk score."""
    if not comparison:
        return False
    counts = comparison["counts"]
    if counts["new"] or counts["worse"]:
        return True
    before = comparison["risk"]["before"]
    after = comparison["risk"]["after"]
    if before in RANK and after in RANK:
        return RANK[after] > RANK[before]
    return False


def next_slot(due, cadence, now):
    """The watch's next slot: one cadence on, skipping any already past."""
    if due + cadence > now:
        return due + cadence
    missed = (now - due) // cadence
    return due + (missed + 1) * cadence


# ---------- one watch, one pass ----------------------------------------

def run_watch(watch, now, checked):
    """Claim, re-check, scan and book one watch. Returns an Outcome."""
    due = watch.next_run_at
    if not claim(watch, now):
        return Outcome(watch, "skipped")

    if not still_verified(watch.domain, checked):
        return _verification_failed(watch, now)
    _verification_passed(watch)

    scan, reason = scan_now(watch)
    if reason:
        watch.last_error = reason
        watch.save(update_fields=["last_error"])
        if watch.consecutive_failures >= Watch.MAX_FAILURES:
            watch.pause(Watch.PAUSED_FAILURES)
            return Outcome(watch, "paused", reason=reason, scan=scan)
        return Outcome(watch, "failed", reason=reason, scan=scan)

    cadence = effective_plan(watch.user).watch_cadence
    watch.consecutive_failures = 0
    watch.last_error = ""
    watch.last_run_at = scan.completed_at
    watch.last_scan = scan
    watch.next_run_at = next_slot(due, cadence, timezone.now())
    watch.save(update_fields=[
        "consecutive_failures",
        "last_error",
        "last_run_at",
        "last_scan",
        "next_run_at",
    ])
    comparison = comparison_for(scan)
    return Outcome(
        watch,
        "complete",
        scan=scan,
        comparison=comparison,
        worse=got_worse(comparison),
    )


def run_pass(budget_seconds=BUDGET_SECONDS, clock=time.monotonic,
             now=None):
    """
    One pass over the due watches. Stops picking up new ones once
    budget_seconds have gone by; those are counted in `left`.
    """
    started = clock()
    now = now or timezone.now()
    summary = PassSummary(stale=sweep_stale_scans(now))
    try:
        summary.pulled = len(pull_in(now))
    except Exception:
        # Housekeeping: a bug here never stops the scans that are due.
        logger.exception("Bringing watches forward failed")
    due = due_watches(now)
    summary.due = len(due)
    checked = {}

    for index, watch in enumerate(due):
        if clock() - started >= budget_seconds:
            summary.left = len(due) - index
            break
        try:
            outcome = run_watch(watch, timezone.now(), checked)
        except Exception:
            # One broken watch never stops the others. Its claim
            # already counted a failure and booked a retry.
            logger.exception("Watch %s failed in the runner", watch.pk)
            outcome = Outcome(watch, "failed", reason="runner_error")
        summary.outcomes.append(outcome)
        try:
            # The bell: an alert when the API got worse.
            record_outcome(outcome)
        except Exception:
            logger.exception("No notification for watch %s", watch.pk)

    # Then the emails: one per account, everything the pass found for it. Never raises.
    summary.emails = send_watch_emails(summary.outcomes)
    return summary
