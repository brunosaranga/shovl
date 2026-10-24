import hashlib
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from scans.compare import target_key


def watch_key(url):
    """
    
    Which API an address is, for matching a watch to its scans: the same rule as "since your last scan" (scans/compare.py: host, port unless default, path, query; http and https count as one), stored as a SHA-256 digest so the database can index it whatever the URL's length. None for an address without a host.
    
    """
    key = target_key(url)
    if key is None:
        return None

    # Validated URLs have no control characters, so a newline can't appear inside a part.
    return hashlib.sha256("\n".join(key).encode("utf-8", "surrogatepass")).hexdigest()



class Watch(models.Model):
    """
    
    One API that shovl watch scans on a schedule, for one account.

    A watch runs when all of these hold:

        the account's switch is on          user.watch_enabled (Settings > shovl watch)
        the account still wants this API    active(off = turned off, or swapped for another)
        it fits the plan                    among the account's first N active watches by activated_at, N from accounts/plans.py Worked out
                                            on every run, never stored, so an upgrade or a failed payment changes it without touching a row
        it is not passed                    paused_reason is empty
        it is due                           next_run_at has passed

    Paused means it needs the person: the domain stopped passing verification, or several runs in a row failed. Those show under "needs action" in the bell, and resume() startsit again.

    The address is matched like ":since your last scan", so a watch of https://api.example.com/v1 is the same API as http://API.example.com/v1/.
        

    """


    MAX_FAILURES = 3

    PAUSED_VERIFICATION = "verification"
    PAUSED_FAILURES = "failures"
    PAUSED_CHOICES = [
        ("", "Not paused"),
        (PAUSED_VERIFICATION, "Domain verification no longer passes"),
        (PAUSED_FAILURES, f"Failed {MAX_FAILURES} runs in a row"),
    ]


    # -------- the fields -------------
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watches",
    )

    # The verified domain the API is on. Deleting the domain deletes its watches.
    domain = models.ForeignKey(
        "domains.Domain",
        on_delete=models.CASCADE,
        related_name="watches",
    )

    # What gets scanned: the address of the scan that started the watch (or of the latest mannual scan of the same API). 2048 matches scans/validators.py.
    target_url = models.URLField(max_length=2048)

    # watch_key(target_url), set in save(). One watch per API per account.
    target_key = models.CharField(max_length=64, editable=False)

    active = models.BooleanField(
        default=True,
        help_text="Off: the person turned this API off, or chose to watch another one instead.",
    )

    # Plan slots go to the earlist activated watches. Turning a watch back on puts it last.
    activated_at = models.DateTimeField(default=timezone.now)

    # When the next scheduled scan is due. Defaults to now: a watch added by hand in the admin runs at the next scheduled run.
    next_run_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    # The newest scheduled scan of this watch/ The scan's own history stays in scans/
    last_scan = models.ForeignKey(
        "scans.Scan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    consecutive_failures = models.PositiveSmallIntegerField(default=0)

    paused_reason = models.CharField(max_length=20, choices=PAUSED_CHOICES, blank=True, default="")
    paused_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name_plural = "watches"
        ordering = ["activated_at", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["user", "target_key"], name="watch_one_per_api"),
        ]

    def __str__(self):
        return self.target_url

    @property
    def is_paused(self):
        return bool(self.paused_reason)


    def clean(self):
        super().clean()
        errors = {}
        key = watch_key(self.target_url) if self.target_url else None
        if key is None:
            errors["target_url"] = "Enter a full address, with http:// or https:// and a host name."
        elif self.domain_id and urlsplit(self.target_url).hostname != self.domain.hostname.lower():
            errors["target_url"] = f"The address must be on {self.domain.hostname}."
        elif self.user_id and Watch.objects.filter(user_id=self.user_id, target_key=key).exclude(pk=self.pk).exists():
            # Checked here because the database rule's key is only filled in by save(): without this, the admin would crash on a duplicate instead of saying so.
            errors["target_url"] = "This account already watches this API."
        if self.domain_id and self.user_id and self.domain.user_id != self.user_id:
            errors["domain"] = "This domain belongs to another account."
        elif self.domain_id and self._state.adding and not self.domain.verified:
            errors["domain"] = "Only a verified domain can be watched."
        if errors:
            raise ValidationError(errors)


    def save(self, *args, **kwargs):
        # Every path that stores a wach ends here, so the key always matches the address.
        key = watch_key(self.target_url)
        if key is None:
            raise ValueError("A watch needs an address with a host name.")
        self.target_key = key
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "target_url" in update_fields:
            kwargs["update_fields"] = set(update_fields) | {"target_key"}
        super().save(*args, **kwargs)


    def pause(self, reason, now=None):
        """Stop scheduled scans until the person does something about it."""
        if reason not in (self.PAUSED_VERIFICATION, self.PAUSED_FAILURES):
            raise ValueError(f"Unknown pause reason: {reason!r}")
        self.paused_reason = reason
        self.paused_at = now or timezone.now()
        self.save(update_fields=["paused_reason", "paused_at"])


    def resume(self, now=None):
        """Start again with a clean slate, due at the next scheduled run."""
        now = now or timezone.now()
        self.paused_reason = ""
        self.paused_at = None
        self.consecutive_failures = 0
        self.next_run_at = now
        self.save(update_fields=["paused_reason", "paused_at", "consecutive_failures", "next_run_at"])