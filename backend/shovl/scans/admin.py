from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Scan, ScanFeedback


@admin.register(ScanFeedback)
class ScanFeedbackAdmin(admin.ModelAdmin):
    """
    Answers to "was this report useful?", next to what the report showed. Read-only: these
    are what people said. The scan link disappears once the scan is deleted (guest clean-up
    after 30 days, or a deleted account); the answer and its copy of the report stay.
    """

    list_display = (
        "created_at",
        "useful_answer",
        "would_pay",
        "short_comment",
        "risk_score",
        "counts",
        "practice_target",
        "guest",
        "scan_link",
    )
    list_filter = ("useful", "would_pay", "risk_score", "practice_target", "guest")
    search_fields = ("comment",)
    date_hierarchy = "created_at"
    readonly_fields = [field.name for field in ScanFeedback._meta.fields] + ["scan_link"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="useful", ordering="useful")
    def useful_answer(self, obj):
        return "yes" if obj.useful else "not really"

    @admin.display(description="comment")
    def short_comment(self, obj):
        text = obj.comment or ""
        return text if len(text) <= 80 else text[:79] + "…"

    @admin.display(description="H / M / L / pass / could not run")
    def counts(self, obj):
        s = obj.summary or {}
        return " / ".join(str(s.get(key, 0)) for key in ("HIGH", "MEDIUM", "LOW", "PASS", "ERROR"))

    @admin.display(description="scan")
    def scan_link(self, obj):
        if not obj.scan_id:
            return "deleted"
        url = reverse("admin:scans_scan_change", args=[obj.scan_id])
        return format_html('<a href="{}">#{}</a>', url, obj.scan_id)


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    """Scans, to look at what a report showed. Read-only: results are what the scanner saved."""

    list_display = ("id", "target_url", "user", "status", "trigger", "risk_score", "pdf_downloads", "created_at")
    list_filter = ("status", "trigger", "risk_score")
    search_fields = ("target_url", "user__email")
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    readonly_fields = [field.name for field in Scan._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
