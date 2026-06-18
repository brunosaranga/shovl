from django.db import models
from django.conf import settings


# Create your models here.
class Scan(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("complete", "Complete"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scans"
    )
    target_url = models.URLField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verbose = models.BooleanField(default=False)
    suggest_fix = models.BooleanField(default=False)
    risk_score = models.CharField(max_length=20, blank=True)
    results = models.JSONField(null=True, blank=True)
    pdf_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.target_url} - {self.status}"

