from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    One item of news in the bell: stored, read or unread, and quieted by
    the account's mute (the badge stops counting news; it still lands
    here). Items that need action are not stored: notifications/services.py
    works them out from the current state on every request.

    title and summary are plain language, safe to show as they are; data
    keeps the details (the comparison of an alert, say), so an item still
    makes sense after its watch or scan is deleted.
    """

    KIND_WATCH_ON = "watch_on"
    KIND_NOW_WATCHING = "now_watching"
    KIND_ALERT = "alert"
    KIND_CHOICES = [
        (KIND_WATCH_ON, "shovl watch is on (once per account)"),
        (KIND_NOW_WATCHING, "Now watching another API"),
        (KIND_ALERT, "A watched API got worse"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    watch = models.ForeignKey(
        "watch.Watch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    scan = models.ForeignKey(
        "scans.Scan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["user", "read_at"],
                name="notification_unread",
            ),
        ]

    def __str__(self):
        return self.title
