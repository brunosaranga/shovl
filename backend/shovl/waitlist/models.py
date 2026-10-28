from django.conf import settings
from django.db import models


class WaitlistEntry(models.Model):
    """
    Someone who asked to hear, once, when xikomu officially launches (waitlist/services.py).

    Pending until its address is proven: a click on the confirmation email's button, or the
    account's own code when the box was ticked at sign-up. Only confirmed entries ever get the
    launch email. What's kept is what the consent needs to be provable: the address, the first
    name, the exact wording agreed to and when, how it was confirmed. No IP addresses.

    Deleted: pending ones after 7 days, everyone when they use "remove me", and the whole list
    about a month after the launch email (accounts/management/commands/purge_guests.py).
    """

    SOURCE_AFTER_SCAN = "after_scan"
    SOURCE_REGISTRATION = "registration"
    SOURCE_CHOICES = [
        (SOURCE_AFTER_SCAN, "After a scan (the modal)"),
        (SOURCE_REGISTRATION, "Ticked at sign-up"),
    ]

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    # The account that ticked the box at sign-up: its confirmed address confirms the entry.
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    consent_version = models.CharField(max_length=20)
    consent_text = models.TextField()
    agreed_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    # The confirmation link's token, as a SHA-256 digest: single use, CONFIRM_LINK_LIFETIME.
    token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    confirm_emails_sent = models.PositiveSmallIntegerField(default=0)
    last_confirm_email_at = models.DateTimeField(null=True, blank=True)
    launch_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "launch list entry"
        verbose_name_plural = "launch list"

    def __str__(self):
        return self.email

    @property
    def confirmed(self):
        return self.confirmed_at is not None
