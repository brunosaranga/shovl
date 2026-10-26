"""
The bell's rules.

News (stored, read or unread, quieted by mute):
    watch_started(watch, automatic)  "murindzi is on" once per account,
                                     then "now watching ..." for later
                                     watches that started by themselves
    record_outcome(outcome)          the runner's results: an alert when
                                     a watched API got worse

Needs action (worked out on every request, never stored, never muted):
    needs_action(user)   pending domains (the unverified cache), domains
                         that lost verification (rule A, one item each,
                         with their paused watches) and watches paused
                         after failed runs

    badge(user)          what the bell's badge shows
"""
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.plans import effective_plan
from domains.models import Domain
from scanner.http import MESSAGES
from watch.models import Watch

from .models import Notification

ONE_LINER = (
    "murindzi re-scans your API on a schedule and tells you when "
    "something gets worse."
)

# Why a watch's last run failed, as a sentence (watch.last_error -> text).
ERRORS = {
    **MESSAGES,
    "verification": "The domain's verification record wasn't found.",
    "scan_error": "The scan hit an unexpected problem.",
    "stopped": "The scan was stopped.",
}

TITLE_MAX = 200


def where(url):
    """Host and path: short, and never the query string (it can hold keys)."""
    parts = urlsplit(url or "")
    return f"{parts.hostname or ''}{parts.path or '/'}"


def _title(text):
    if len(text) <= TITLE_MAX:
        return text
    return text[:TITLE_MAX - 1] + "…"


def _every(days):
    return "every day" if days == 1 else f"every {days} days"


# ---------- news ---------------------------------------------------------

def watch_started(watch, automatic):
    """
    A watch started. The account's first one ever brings the
    announcement (watch_intro_at is set in the same step, so it can never
    go out twice). Later ones get "now watching ..." when they started
    by themselves; one the person started gets nothing: they just did it.
    """
    user = watch.user
    days = effective_plan(user).watch_cadence.days
    first = get_user_model().objects.filter(
        pk=user.pk, watch_intro_at__isnull=True
    ).update(watch_intro_at=timezone.now())

    if first:
        return Notification.objects.create(
            user=user,
            kind=Notification.KIND_WATCH_ON,
            watch=watch,
            title=_title(f"murindzi is on for {where(watch.target_url)}"),
            summary=(
                f"{ONE_LINER} It's scanned {_every(days)} on your plan. "
                "Turn it off any time in settings."
            ),
            data={"target_url": watch.target_url, "cadence_days": days},
        )
    if automatic:
        return Notification.objects.create(
            user=user,
            kind=Notification.KIND_NOW_WATCHING,
            watch=watch,
            title=_title(f"now watching {where(watch.target_url)}"),
            summary=(
                f"Scanned {_every(days)}. Manage your watched APIs in "
                "settings."
            ),
            data={"target_url": watch.target_url, "cadence_days": days},
        )
    return None


def _names(changes, kind):
    names = [c["check"] for c in changes if c["change"] == kind]
    if len(names) > 3:
        names = names[:3] + [f"{len(names) - 3} more"]
    return ", ".join(names)


def alert_summary(comparison):
    risk = comparison["risk"]
    parts = []
    if risk["before"] != risk["after"]:
        parts.append(f"Risk {risk['before']} → {risk['after']}.")
    new = _names(comparison["checks"], "new")
    worse = _names(comparison["checks"], "worse")
    if new:
        parts.append(f"New problem: {new}.")
    if worse:
        parts.append(f"Worse: {worse}.")
    return " ".join(parts)


def record_outcome(outcome):
    """An alert when a scheduled scan found the API worse. Else nothing."""
    if outcome.result != "complete" or not outcome.worse:
        return None
    scan, comparison = outcome.scan, outcome.comparison
    changes = [
        c for c in comparison["checks"] if c["change"] in ("new", "worse")
    ]
    return Notification.objects.create(
        user=outcome.watch.user,
        kind=Notification.KIND_ALERT,
        watch=outcome.watch,
        scan=scan,
        title=_title(f"{where(scan.target_url)} got worse"),
        summary=alert_summary(comparison),
        data={
            "target_url": scan.target_url,
            "risk": comparison["risk"],
            "counts": comparison["counts"],
            "changes": changes,
            "previous_scan_id": comparison["previous"]["id"],
        },
    )


# ---------- needs action ---------------------------------------------------

def needs_action(user):
    """
    What needs the person, most urgent first. Each item: key (stable, for
    lists), kind, title, summary, actions (the buttons), and the ids the
    buttons need.

        domain_lost_verification   rule A: the record went missing.
                                   actions: verify, remove
        watch_paused               3 failed runs. action: resume
        domain_pending             verifying never finished (the
                                   unverified cache). actions: verify,
                                   remove
    """
    if user.is_guest:
        return []

    paused = list(
        Watch.objects.filter(user=user, active=True)
        .exclude(paused_reason="")
        .select_related("domain")
    )
    lost, waiting, items = {}, [], []
    for domain in Domain.objects.filter(user=user, verified=False):
        mine = [w for w in paused if w.domain_id == domain.pk]
        if mine:
            lost[domain.pk] = (domain, mine)
        else:
            waiting.append(domain)

    for domain, watches in lost.values():
        if len(watches) == 1:
            which = "its watch is"
        else:
            which = f"its {len(watches)} watches are"
        items.append({
            "key": f"domain:{domain.pk}",
            "kind": "domain_lost_verification",
            "title": f"verification no longer passes: {domain.hostname}",
            "summary": (
                f"The verification record wasn't found {Watch.MAX_FAILURES} "
                f"times in a row, so the domain is back to pending and "
                f"{which} paused. Put the record back, then verify again "
                "to resume."
            ),
            "actions": ["verify", "remove"],
            "domain_id": domain.pk,
            "hostname": domain.hostname,
            "watch_ids": [w.pk for w in watches],
        })

    if user.watch_enabled:
        for watch in paused:
            if watch.domain_id in lost:
                continue
            reason = ERRORS.get(watch.last_error, ERRORS["error"])
            items.append({
                "key": f"watch:{watch.pk}",
                "kind": "watch_paused",
                "title": f"watch paused: {where(watch.target_url)}",
                "summary": (
                    f"The last {Watch.MAX_FAILURES} scheduled scans "
                    f"failed. {reason} Resume once the API is reachable."
                ),
                "actions": ["resume"],
                "watch_id": watch.pk,
            })

    for domain in sorted(waiting, key=lambda d: d.created_at, reverse=True):
        items.append({
            "key": f"domain:{domain.pk}",
            "kind": "domain_pending",
            "title": f"unverified domain: {domain.hostname}",
            "summary": "You started verifying this domain but didn't finish.",
            "actions": ["verify", "remove"],
            "domain_id": domain.pk,
            "hostname": domain.hostname,
        })
    return items


def unread_news(user):
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def badge(user, needs=None, unread=None):
    """Needs-action items always count; news only while not muted."""
    needs = needs_action(user) if needs is None else needs
    if user.notifications_muted:
        return len(needs)
    unread = unread_news(user) if unread is None else unread
    return len(needs) + unread
