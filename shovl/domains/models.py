from django.db import models
from django.conf import settings
import secrets

# Create your models here.
class Domain(models.Model):
    VERIFICATION_METHODS = [("dns", "DNS"), ("file", "File")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="domains"
    )
    hostname = models.CharField(max_length=255)
    verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, default=secrets.token_hex)
    verification_method = models.CharField(
        max_length=10, choices=VERIFICATION_METHODS, default="dns"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["user", "hostname"]

    def __str__(self):
        return f"{self.hostname} ({'verified' if self.verified else 'unverified'})"