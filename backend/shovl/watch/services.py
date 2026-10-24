"""
The rules of shovl watch in one place: which APIs can be watched, which watches fit the plan,
what a report says about its API, and what happens when someone watches, swaps, turns off or
resumes one. The views and the scan endpoints call these; nothing else changes Watch rows.

    watch_after_scan(scan)        a manual scan completed: start watching its API if it qualifies
    scan_watch_state(scan)        the badge on a report: watching, paused, off or not watched, and why
    watch_scan(user, scan)        "watch this API" / "watch this one instead" on a report
    set_active(user, watch, on)   Settings: turn one API off, or back on
    resume_watch(watch)           start a paused watch again
    domain_lost_verification(d)   re-checks failed: domain pending, watches off
    domain_verified_again(d)      verified again: those watches start again
"""
import random
from datetime import timedelta
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.plans import effective_plan
from domains.models import Domain
from notifications.services import watch_started
from domains.verification import is_practice_target
from scans.models import TRIGGER_MANUAL

from .models import Watch, watch_key

# A watch's runs are spread over this much time after its slot, so a rush of scans finishing
# together (a post going out, say) doesn't land in one runner pass.
SPREAD = timedelta(hours=1)


class WatchRefused(Exception):
    """Raised when a watch can't be started or turned on. Carries what the view needs."""

    def __init__(self, code, http_status, detail, **extra):
        super().__init__(detail)
        self.code = code
        self.http_status = http_status
        self.detail = detail
        self.extra = extra

    def as_response_data(self):
        return {"detail": self.detail, "code": self.code, **self.extra}


# ---------- small helpers ----------------------------------------------------------------

def verified_domain_for(user, url):
    """The account's verified domain for this address, or None (guests and practice targets never have one)."""
    host = urlsplit(url or "").hostname
    if not host or user.is_guest or is_practice_target(url):
        return None
    return Domain.objects.filter(user=user, hostname=host, verified=True).first()


def in_plan_ids(user, plan=None):
    """Ids of the watches that fit the plan: the account's first N active watches by activation."""
    plan = plan or effective_plan(user)
    active = Watch.objects.filter(user=user, active=True).order_by("activated_at", "pk").values_list("pk", flat=True)
    if plan.watch_slots is None:
        return set(active)
    return set(active[:plan.watch_slots])


def has_room(user, plan=None, leaving_out=None):
    """Whether one more watch can be active. leaving_out: a watch not to count (the one being turned on)."""
    plan = plan or effective_plan(user)
    if plan.watch_slots is None:
        return True
    active = Watch.objects.filter(user=user, active=True)
    if leaving_out is not None:
        active = active.exclude(pk=leaving_out.pk)
    return active.count() < plan.watch_slots


def _spread():
    return timedelta(seconds=random.uniform(0, SPREAD.total_seconds()))


def next_run_from(base, plan):
    """The next scheduled scan: one cadence after base, plus a random part of the spread."""
    return base + plan.watch_cadence + _spread()


def _lock_account(user):
    # Two requests (or two scans finishing together) can't both take the last slot. The lock
    # takes effect on Postgres, like the one in scans/limits.py.
    get_user_model().objects.select_for_update().get(pk=user.pk)


def _when(scan):
    return scan.completed_at or scan.created_at


# ---------- a scan completed ---------------------------------------------------------------

def watch_after_scan(scan):
    """
    Called when a manual scan completes. Starts a watch for its API when the scan is of the
    account's own verified domain, the account's switch is on and the plan has room. An API
    that already has a watch keeps it (its address follows the newest scan, http to https say),
    and one the person turned off stays off. Returns the watch covering this API, or None.
    """
    if scan.status != "complete" or scan.trigger != TRIGGER_MANUAL:
        return None
    user = scan.user
    if not user.watch_enabled:
        return None
    domain = verified_domain_for(user, scan.target_url)
    key = watch_key(scan.target_url)
    if domain is None or key is None:
        return None
    plan = effective_plan(user)
    if not plan.can_watch:
        return None

    with transaction.atomic():
        _lock_account(user)
        existing = Watch.objects.filter(user=user, target_key=key).first()
        if existing is not None:
            if existing.target_url != scan.target_url:
                existing.target_url = scan.target_url
                existing.save(update_fields=["target_url"])
            return existing
        if not has_room(user, plan):
            return None
        watch = Watch.objects.create(
            user=user,
            domain=domain,
            target_url=scan.target_url,
            activated_at=timezone.now(),
            next_run_at=next_run_from(_when(scan), plan),
        )
        # The bell: "shovl watch is on" the first time, else "now watching".
        watch_started(watch, automatic=True)
        return watch


# ---------- what a report says -------------------------------------------------------------

def _full_action(plan):
    # One slot: swap it ("watch this one instead"). More: the person picks which to turn off.
    return "swap" if plan.watch_slots == 1 else "settings"


def scan_watch_state(scan):
    """
    The badge on a report, about the scan's API:

        status        watching | paused | off | not_watched
        reason        why it isn't plainly watching (None when it is):
                        paused:      verification | failures
                        off:         account_off (the Settings switch) | turned_off (this API)
                        not_watched: not_started | plan_full | over_plan | unverified
        action        the button to offer: watch | swap | resume | settings | None
        next_run_at   when it's next scanned (watching only)
        cadence_days  days between scans on the account's plan
        watch_slots   APIs the plan watches (None = no limit)
        watch_id      the watch's id, when there is one

    None when there's nothing to say: a practice target, a guest, or an address without a host.
    """
    user = scan.user
    key = watch_key(scan.target_url)
    if user.is_guest or key is None or is_practice_target(scan.target_url):
        return None

    plan = effective_plan(user)
    watch = Watch.objects.filter(user=user, target_key=key).first()

    def state(status, reason=None, action=None):
        return {
            "status": status,
            "reason": reason,
            "action": action,
            "next_run_at": watch.next_run_at if (watch and status == "watching") else None,
            "cadence_days": plan.watch_cadence.days,
            "watch_slots": plan.watch_slots,
            "watch_id": watch.pk if watch else None,
        }

    if watch is None:
        if verified_domain_for(user, scan.target_url) is None:
            return state("not_watched", "unverified")
        if not user.watch_enabled:
            return state("off", "account_off", "settings")
        if has_room(user, plan):
            return state("not_watched", "not_started", "watch")
        return state("not_watched", "plan_full", _full_action(plan))

    if not user.watch_enabled:
        return state("off", "account_off", "settings")
    if watch.is_paused:
        return state("paused", watch.paused_reason, "resume")
    if not watch.active:
        action = "watch" if has_room(user, plan) else _full_action(plan)
        return state("off", "turned_off", action)
    if watch.pk not in in_plan_ids(user, plan):
        # Active, but past the plan's slots: a downgrade, or later a failed payment.
        return state("not_watched", "over_plan", _full_action(plan))
    return state("watching")


# ---------- the person acts ----------------------------------------------------------------

def watch_scan(user, scan, instead=False):
    """
    "watch this API" on a report: start (or turn back on) the watch for the scan's API.
    With instead=True on a one-slot plan, the account's other watches are turned off first
    ("watch this one instead"). Never adds a scan of its own: the next run is one cadence after
    the newest scan of this API that shovl knows about.

    Returns (watch, changed). Raises WatchRefused.
    """
    if user.is_guest:
        raise WatchRefused("registration_required", 403, "Create a free account to watch your own API.")
    if is_practice_target(scan.target_url):
        raise WatchRefused("practice_target", 400, "Practice targets can't be watched.")
    domain = verified_domain_for(user, scan.target_url)
    key = watch_key(scan.target_url)
    if domain is None or key is None:
        raise WatchRefused("domain_not_verified", 403, "Verify this domain to watch its API.")

    plan = effective_plan(user)
    with transaction.atomic():
        _lock_account(user)
        watch = Watch.objects.filter(user=user, target_key=key).first()
        if watch is not None and watch.active and watch.pk in in_plan_ids(user, plan):
            return watch, False

        # This API needs one of the plan's slots, and every one is taken by another watch.
        others = Watch.objects.filter(user=user, active=True)
        if watch is not None:
            others = others.exclude(pk=watch.pk)
        if plan.watch_slots is not None and others.count() >= plan.watch_slots:
            if not (instead and plan.watch_slots == 1):
                raise WatchRefused(
                    "plan_full",
                    409,
                    f"Your plan watches {plan.watch_slots} API{'' if plan.watch_slots == 1 else 's'}.",
                    can_swap=plan.watch_slots == 1,
                    watch_slots=plan.watch_slots,
                )
            others.update(active=False)

        now = timezone.now()
        base = _when(scan)
        if watch is None:
            watch = Watch.objects.create(
                user=user,
                domain=domain,
                target_url=scan.target_url,
                activated_at=now,
                next_run_at=next_run_from(base, plan),
            )
            # The person did this: the bell only says so if it's their first.
            watch_started(watch, automatic=False)
            return watch, True

        # Turned off before, or active but past the plan's slots: bring it back as the newest.
        if watch.last_run_at and watch.last_run_at > base:
            base = watch.last_run_at
        watch.active = True
        watch.activated_at = now
        watch.next_run_at = next_run_from(base, plan)
        watch.save(update_fields=["active", "activated_at", "next_run_at"])
        return watch, True


def set_active(user, watch, active):
    """Settings: turn one API off, or back on (if the plan has room). Returns the watch."""
    if not active:
        if watch.active:
            watch.active = False
            watch.save(update_fields=["active"])
        return watch
    if watch.active:
        return watch

    plan = effective_plan(user)
    with transaction.atomic():
        _lock_account(user)
        if not has_room(user, plan, leaving_out=watch):
            raise WatchRefused(
                "plan_full",
                409,
                "Turn another API off first: your plan's slots are all in use.",
                can_swap=False,
                watch_slots=plan.watch_slots,
            )
        watch.active = True
        watch.activated_at = timezone.now()
        watch.next_run_at = next_run_from(watch.last_run_at or watch.created_at, plan)
        watch.save(update_fields=["active", "activated_at", "next_run_at"])
    return watch


def resume_watch(watch):
    """Start a paused watch again (due at the next runner pass). Returns the watch."""
    if watch.is_paused:
        watch.resume()
    return watch


# ---------- the domain's verification ------------------------------------------------------

def domain_lost_verification(domain, now=None):
    """
    Rule A: the runner's re-check failed MAX_FAILURES times in a row.
    The domain goes back to pending (manual scans of it need verifying
    again too) and every watch on it pauses.
    """
    now = now or timezone.now()
    with transaction.atomic():
        Domain.objects.filter(pk=domain.pk).update(
            verified=False,
            verified_at=None,
        )
        Watch.objects.filter(domain=domain, paused_reason="").update(
            paused_reason=Watch.PAUSED_VERIFICATION,
            paused_at=now,
        )


def domain_verified_again(domain):
    """The domain passed verification again: its paused watches restart."""
    paused = Watch.objects.filter(
        domain=domain,
        paused_reason=Watch.PAUSED_VERIFICATION,
    )
    for watch in paused:
        watch.resume()
