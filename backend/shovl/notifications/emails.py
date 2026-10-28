"""
murindzi's alert emails. After each runner pass (watch/runner.py, run_pass), every account
with something to hear about gets ONE email listing it all:

    worse     a scheduled scan found the API worse (the same rule as the bell's alert)
    domain    the domain's verification record wasn't found 3 times in a row: the domain is
              back to pending and every watch on it paused (rule A)
    failures  3 scheduled scans of one API failed in a row: that watch paused

Who gets it: a registered account whose address is confirmed (accounts/confirmation.py),
with the bell not muted and Settings > murindzi > "email me" on (User.email_alerts).
Everyone else still finds it all in the bell. The mailer adds its own limits on top (10 a
day to one address, the daily cap) and logs every attempt.

Every email has a "turn these emails off" link, also in the List-Unsubscribe header (the
"unsubscribe" that Gmail and others show). The link is signed with the server's secret key,
so it can only ever switch off that one account's emails, and the page it opens asks for a
click first (a POST), because some mail scanners open every link they see.

Nothing here may stop the runner: send_watch_emails never raises.
"""
import logging
from dataclasses import dataclass
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.core import signing

from mailer.services import base_context, send_email
from watch.models import Watch

from .services import ERRORS, alert_summary, where

logger = logging.getLogger("notifications")

KIND = "watch_alert"
SALT = "notifications.email-off"
# How much of an API's address goes in a subject before it's cut with "…".
SUBJECT_TARGET_MAX = 60


@dataclass
class EmailTally:
    """What the pass's emails came to, for the runner's log."""

    sent: int = 0
    not_wanted: int = 0  # muted, switched off, unconfirmed or a guest: the bell only
    not_sent: int = 0  # wanted, but the mailer refused, limited or failed

    def __str__(self):
        return f"{self.sent} sent, {self.not_wanted} not wanted, {self.not_sent} not sent"


# ---------- the "turn these emails off" link ----------------------------------

def off_token(user):
    return signing.dumps({"u": user.pk}, salt=SALT, compress=True)


def user_for_token(token):
    """The account a turn-off link belongs to, or None if the link isn't genuine."""
    try:
        data = signing.loads(str(token or ""), salt=SALT)
        return get_user_model().objects.filter(pk=int(data["u"])).first()
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        return None


def turn_off(token):
    """Switch off one account's alert emails from a link. True if the link was genuine."""
    user = user_for_token(token)
    if user is None:
        return False
    get_user_model().objects.filter(pk=user.pk).update(email_alerts=False)
    return True


# ---------- who, and what ---------------------------------------------------

def wants_email(user):
    return (
        user.is_active
        and not user.is_guest
        and user.email_confirmed_at is not None
        and not user.notifications_muted
        and user.email_alerts
    )


def _short(text, limit=SUBJECT_TARGET_MAX):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _domain_summary(domain):
    paused = Watch.objects.filter(domain=domain, paused_reason=Watch.PAUSED_VERIFICATION).count()
    which = "its watch is" if paused == 1 else f"its {paused} watches are"
    return (
        f"The verification record wasn't found {Watch.MAX_FAILURES} times in a row, so the "
        f"domain is back to pending and {which} paused. Put the record back, then verify the "
        "domain again in xikomu to resume."
    )


def items_by_account(outcomes, site_url):
    """
    {user id: [item, ...]} from a pass's outcomes. An item: kind, where (host and path only,
    never the query string, which can hold keys), summary, and link (where to act).
    """
    found = {}
    domains_done = set()
    settings_url = f"{site_url}/settings" if site_url else ""

    for outcome in outcomes:
        watch = outcome.watch
        item = None
        if outcome.result == "complete" and outcome.worse and outcome.scan and outcome.comparison:
            item = {
                "kind": "worse",
                "where": where(outcome.scan.target_url),
                # "worse" is only ever true with a comparison (watch/runner.py, got_worse).
                "summary": alert_summary(outcome.comparison),
                "link": f"{site_url}/scan/{outcome.scan.pk}/report" if site_url else "",
                "action": "open the report",
            }
        elif outcome.result == "paused" and outcome.reason == "verification":
            if watch.domain_id in domains_done:
                continue  # one item per domain, however many of its watches were paused
            domains_done.add(watch.domain_id)
            item = {
                "kind": "domain",
                "where": watch.domain.hostname,
                "summary": _domain_summary(watch.domain),
                "link": settings_url,
                "action": "open settings",
            }
        elif outcome.result == "paused":
            reason = ERRORS.get(watch.last_error, ERRORS["error"])
            item = {
                "kind": "failures",
                "where": where(watch.target_url),
                "summary": (
                    f"The last {Watch.MAX_FAILURES} scheduled scans failed. {reason} "
                    "Resume it in settings once the API is reachable."
                ),
                "link": settings_url,
                "action": "open settings",
            }
        if item:
            found.setdefault(watch.user_id, []).append(item)
    return found


def headline(items):
    """The subject's text, written by the server from the account's own items."""
    if len(items) > 1:
        return f"{len(items)} updates from murindzi"
    item = items[0]
    if item["kind"] == "worse":
        return f"{_short(item['where'])} got worse"
    return f"murindzi paused {_short(item['where'])}"


# ---------- sending ---------------------------------------------------------

def send_watch_emails(outcomes):
    """One email per account with something to hear about. Returns an EmailTally."""
    tally = EmailTally()
    try:
        site_url = base_context()["site_url"]
        found = items_by_account(outcomes, site_url)
        users = get_user_model().objects.in_bulk(list(found))
    except Exception:
        logger.exception("murindzi's emails: couldn't work out who to email")
        return tally

    for user_id, items in found.items():
        user = users.get(user_id)
        if user is None or not wants_email(user):
            tally.not_wanted += 1
            continue
        try:
            off_url = f"{site_url}/email-off?t={quote(off_token(user))}" if site_url else ""
            result = send_email(
                KIND,
                user.email,
                {
                    "headline": headline(items),
                    "items": items,
                    "off_url": off_url,
                    "settings_url": f"{site_url}/settings" if site_url else "",
                },
                user=user,
                headers={"List-Unsubscribe": f"<{off_url}>"} if off_url else None,
            )
        except Exception:
            logger.exception("murindzi's email to account %s failed", user_id)
            tally.not_sent += 1
            continue
        if result.sent:
            tally.sent += 1
        else:
            tally.not_sent += 1
    return tally
