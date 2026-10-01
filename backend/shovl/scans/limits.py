"""
Scan allowance for the beta.

    guests                      3 scans in total
    registered_users            5 scans in any rolling 24 hours

    A scan counts from the moment it starts. Scans that failed or were interrupted do not count, but every attempt couunts toward a higher hard ceiling, so failures cannot be used for unlimited free scanning. Staff accounts are exempt.

    Change the nu,bers below, nothing else needs to move.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Scan

User = get_user_model()


# ---------- the numbers -----------------------
GUEST_SCANS_TOTAL = 3
USER_SCANS_PER_DAY = 5



# ---------- hard ceilings, failed and interrupted attempts included -----------------------
GUEST_ATTEMPTS_TOTAL = 6
USRE_ATTEMPTS_PER_DAY = 10

DAY = timedelta(hours=24)




# A scan still "running" after this long is treated as abandoned 
STALE_AFTER = timedelta(minutes=10)
# ---------------------------------------------------------------

IN_PROGRESS = ("pending", "running")



class AllowanceExceeded(Exception):
    """Raised by start_scan. Carries what the view needs to build the refusal."""

    def __init__(self, code, http_status, detail, retry_after=None):
        super().__init__(detail)
        self.code = code
        self.http_status = http_status
        self.detail = detail
        self.retry_after = retry_after


    def as_response_data(self):
        data = {"detail": self.detail, "code": self.code}
        if self.retry_after is not None:
            data["retry_after"] = self.retry_after.isoformat()
        return data




def _scope(user, now):
    """Every scan that could count for this user: all of a guest's, or a registered user's last 24 hours. """
    scans = Scan.objects.filter(user=user)
    if not user.is_guest:
        scans = scans.filter(created_at__gte=now - DAY)
    return scans



def _counted(scans, now):
    """Complete scans, plus ones genuinely in progress. Failed, interrupted and stale ones do not count."""
    return scans.filter(
        Q(status="complete")
        | Q(status__in=IN_PROGRESS, created_at__gte=now - STALE_AFTER)
    )



def _frees_up_at(scans):
    """When the oldest scan in the window ages out, so the person can try again."""
    oldest = scans.order_by("created_at").first()
    return oldest.created_at + DAY if oldest else None



def scans_remaining(user):
    """
    For the frontend: {"limit", "used", "remaining", "period"}, or None when the account has no limit. Read-only, so it is safe to call on every /me/ request.
    """
    if user.is_staff:
        return None
    
    now = timezone.now()
    used = _counted(_scope(user, now), now).count()
    limit = GUEST_SCANS_TOTAL if user.is_guest else USER_SCANS_PER_DAY

    return {
        "limit": limit,
        "used": used,
        "remaining": max(limit - used, 0),
        "period": "total" if user.is_guest else "day",
    }



def start_scan(user, **fields):
    """
    Checks the allowance and create the scan record, as one locked step so that simultaneous requests cannot all slip under the limit (the lock takes effect on Postgres). Returns the new Scan with status "running", or raises AllowanceExceeded.
    """
    if user.is_staff:
        return Scan.objects.create(user=user, status="running", **fields)

    now = timezone.now()

    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)

        scans = _scope(user, now)

        # Anything still "running" long after it started was abondoned.
        scans.filter(
            status__in=IN_PROGRESS, created_at__lt=now - STALE_AFTER
        ).update(status="interrupted")

        if user.is_guest:
            allowance, ceiling = GUEST_SCANS_TOTAL, GUEST_ATTEMPTS_TOTAL
        else:
            allowance, ceiling = USER_SCANS_PER_DAY, USRE_ATTEMPTS_PER_DAY

        if _counted(scans, now).count() >= allowance:
            if user.is_guest:
                raise AllowanceExceeded(
                    "guest_limit_reached",
                    403,
                    f"You've used your {allowance} free scans. Create a free account to keep going.",
                )
            raise AllowanceExceeded(
                "daily_limit_reached",
                429,
                f"You've used today's {allowance} scans. Try again once the next one frees up.",
            )

        if scans.count() >= ceiling:
            if user.is_guest:
                raise AllowanceExceeded(
                    "guest_limit_reached",
                    403,
                    "Too many scan attempts. Create a free account to keep going."
                )
            raise AllowanceExceeded(
                "too_many_attempts",
                429,
                "Too many scan attempts today. Try again later.",
                retry_after=_frees_up_at(scans),
            )

        return Scan.objects.create(user=user, status="running", **fields)