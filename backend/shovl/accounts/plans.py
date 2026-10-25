"""

What each plan includes, and which plan an account actually gets right now.

    plan    watched APIs    time between two scheduled scans of one API
    guest   0               (guests cannot verify a domain, so they never watch one)
    free    1               30 days (WATCH_FREE_CADENCE_DAYS: 7 during the beta)
    pro     5               7 days
    staff   no limit        7 days

The one rule: every feature that depends on the plan asks effective_plan(user), never user.plan. user.plan is what theaccount signed up for; effective_plan is what it gets today. When billing arrives, a failed payment is checked in one place (pro_is_paid below) and evry Pro feature falls back to the Free together, without deleting anything: watches over the Free limit stop running and start again as soon as the payment goes through.

Change the numbers below, nothing else needs to move.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings


# ---------- the numbers ---------------------------
FREE_WATCH_SLOTS = 1
PRO_WATCH_SLOTS = 5
PRO_WATCH_CADENCE_DAYS = 7
# The free plan's cadence lives in settings (SHOVL_WATCH_FREE_CADENCE_DAYS, read from the WATCH_FREE_CADENCE_DAYS environment variable), so the beta can run weekly without a deploy.
# --------------------------------------------------



@dataclass(frozen=True)
class Plan:
    name: str
    # How many APIs shovll watch keeps scanning. None = no limit
    watch_slots: int | None
    # Time between two scheduled scans of one API
    watch_cadence: timedelta

    @property
    def can_watch(self):
        return self.watch_slots is None or self.watch_slots > 0


def _pro_cadence():
    return timedelta(days=PRO_WATCH_CADENCE_DAYS)


def _free_cadence():
    # Read on every call, not at import, so a changed setting (or a test) takes effect at once.
    return timedelta(days=settings.SHOVL_WATCH_FREE_CADENCE_DAYS)


def guest_plan():
    return Plan("guest", 0, _free_cadence())

def free_plan():
    return Plan("free", FREE_WATCH_SLOTS, _free_cadence())

def pro_plan():
    return Plan("pro", PRO_WATCH_SLOTS, _pro_cadence())

def staff_plan():
    return Plan("staff", None, _pro_cadence())


def pro_is_paid(user):
    """
    Whether a Pro account's payment is in order.

    Billing does not exist yet: Pro is handed out by hand in the admin, so it always counts as paid. When Paddle arrives, this reads the subscription (a failed renewal, after any grace period, returns False) and nothing else in the app changes.

    """
    return True


def effective_plan(user):
    """The plan this account gets right now. Every plan-dependent feature asks this."""
    if user.is_staff:
        return staff_plan()
    if user.is_guest:
        return guest_plan()
    if user.plan == user.PLAN_PRO and pro_is_paid(user):
        return pro_plan()
    return free_plan()

