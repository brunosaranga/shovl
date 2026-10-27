from django.conf import settings
from django.db import models


class SentEmail(models.Model):
    """
    One attempt to send an email, whatever happened to it. The limits in mailer/services.py
    count these rows, and the admin shows them so the day's use of Brevo's free allowance is
    visible.

    The address itself is never stored: to_hash is a keyed hash of it (mailer/services.py,
    address_hash), enough to count what went to one address and nothing more. user links the
    row to an account when there is one. Rows are deleted after 90 days
    (accounts/management/commands/purge_guests.py, run daily).
    """

    STATUS_SENT = "sent"          # handed to Brevo, which accepted it
    STATUS_FAILED = "failed"      # Brevo (or the network) refused or errored
    STATUS_LIMITED = "limited"    # not sent: too many to this address, or the daily cap
    STATUS_REFUSED = "refused"    # not sent: an address that must never be emailed
    STATUS_DISABLED = "disabled"  # not sent: no Brevo key on this server
    STATUS_CHOICES = [
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
        (STATUS_LIMITED, "Not sent: limit reached"),
        (STATUS_REFUSED, "Not sent: address refused"),
        (STATUS_DISABLED, "Not sent: email switched off"),
    ]

    kind = models.CharField(max_length=40)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    to_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    message_id = models.CharField(max_length=200, blank=True)
    error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            # "how many of this kind went to this address lately?"
            models.Index(fields=["to_hash", "kind", "created_at"], name="sentemail_address"),
            # "how many went out in the last 24 hours?"
            models.Index(fields=["status", "created_at"], name="sentemail_status"),
        ]

    def __str__(self):
        return f"{self.kind} · {self.get_status_display()} · {self.created_at:%Y-%m-%d %H:%M}"
