from django.conf import settings
from django.contrib import admin
from django.utils import timezone

from .models import SentEmail
from .services import DAY


@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    """
    Every email xikomu tried to send, and what happened. Read-only: these are records. The
    title shows the last 24 hours against EMAIL_DAILY_CAP (Brevo's free plan allows 300 a day,
    replies sent from Gmail included).
    """

    list_display = ("created_at", "kind", "status", "user", "short_hash", "message_id", "error")
    list_filter = ("kind", "status")
    search_fields = ("user__email", "message_id")
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in SentEmail._meta.fields]

    @admin.display(description="address (hashed)")
    def short_hash(self, obj):
        return f"{obj.to_hash[:12]}…"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        sent = SentEmail.objects.filter(
            status=SentEmail.STATUS_SENT, created_at__gte=timezone.now() - DAY
        ).count()
        extra_context = {
            **(extra_context or {}),
            "title": f"Emails: {sent} sent in the last 24 hours (cap {settings.EMAIL_DAILY_CAP})",
        }
        return super().changelist_view(request, extra_context)
