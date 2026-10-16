from django.db import models
from django.conf import settings

from .encoders import StorableJSONEncoder


# A scan in one of these has not ended yet. Pause and stop only apply to these, and the
# allowance counts them while they last (scans/limits.py).
ACTIVE_STATUSES = ("pending", "running", "paused")


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
    pdf_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.target_url} - {self.status}"

