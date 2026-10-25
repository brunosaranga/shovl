from django.db import models
from django.conf import settings

from .encoders import StorableJSONEncoder


# A scan in one of these has not ended yet. Pause and stop only apply to these, and the
# allowance counts them while they last (scans/limits.py).
ACTIVE_STATUSES = ("pending", "running", "paused")

# What started a scan. Scheduled scans (shovll watch) never count against the allowance.
TRIGGER_MANUAL = "manual"
TRIGGER_WATCH = "watch"


# Create your models here.
class Scan(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        # Held between two checks until the person resumes or stops it (scans/controls.py).
        ("paused", "Paused"),
        ("complete", "Complete"),
        ("failed", "Failed"),
        # The browser closed (or the scan was abandoned) before it finished.
        ("interrupted", "Interrupted"),
        # Ended on purpose: the stop button, or paused for too long. Results hold the reason.
        ("stopped", "Stopped"),
    ]
    TRIGGER_CHOICES = [
        (TRIGGER_MANUAL, "Manual"),
        (TRIGGER_WATCH, "shovll watch"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scans"
    )
    # 2048 matches scans/validators.py. Postgres enforces the length; SQLite never did.
    target_url = models.URLField(max_length=2048)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verbose = models.BooleanField(default=False)
    suggest_fix = models.BooleanField(default=False)
    risk_score = models.CharField(max_length=20, blank=True)
    results = models.JSONField(null=True, blank=True, encoder=StorableJSONEncoder)
    # No longer written: PDFs are built when someone downloads one (GET /api/scans/<id>/pdf/).
    # Kept so files saved by older versions can still be cleaned up (purge_guests).
    pdf_path = models.CharField(max_length=500, blank=True)
    # How many times this report was downloaded as a PDF. For the beta question "do people
    # want a report they can hand over?": see which scans (own domains or practice) get them.
    pdf_downloads = models.PositiveIntegerField(default=0)
    # "manual": started from the app. "watch": run on a schedule by shovll watch (watch/),
    # which shows on the dashboard and in "since your last scan" but not in the allowance.
    trigger = models.CharField(max_length=10, choices=TRIGGER_CHOICES, default=TRIGGER_MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.target_url} - {self.status}"


class ScanFeedback(models.Model):
    """
    The optional "was this report useful?" answer at the bottom of a report. One per scan.

    Each answer keeps a copy of what the report showed (risk score, counts, options), so it
    still means something after the scan is gone. Deleting the scan (the daily guest clean-up,
    or an account being deleted) empties `scan` and keeps the answer, with nothing that points
    to the person or the scanned address. The comment is whatever the person typed.
    """

    WOULD_PAY_CHOICES = [
        ("yes", "Yes"),
        ("maybe", "Maybe"),
        ("no", "No"),
    ]
    COMMENT_MAX_LENGTH = 500

    scan = models.OneToOneField(
        Scan,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedback",
    )
    useful = models.BooleanField(help_text="Yes = useful, No = not really.")
    comment = models.TextField(blank=True, max_length=COMMENT_MAX_LENGTH)
    would_pay = models.CharField(
        max_length=5,
        choices=WOULD_PAY_CHOICES,
        blank=True,
        help_text="Would pay for weekly scans with an email when something changes.",
    )

    # What the report showed when the answer was given.
    risk_score = models.CharField(max_length=20, blank=True)
    summary = models.JSONField(default=dict, blank=True, help_text="Findings per severity.")
    checks_run = models.PositiveSmallIntegerField(null=True, blank=True)
    total_checks = models.PositiveSmallIntegerField(null=True, blank=True)
    practice_target = models.BooleanField(default=False)
    guest = models.BooleanField(default=False, help_text="Answered from a guest session.")
    options = models.JSONField(default=dict, blank=True, help_text="The scan's knobs.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "report feedback"
        verbose_name_plural = "report feedback"

    def __str__(self):
        return f"{'useful' if self.useful else 'not really'} ({self.risk_score or 'no score'})"

