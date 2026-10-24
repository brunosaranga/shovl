from django.contrib import admin
from django.utils import timezone

from .models import Watch


@admin.register(Watch)
class WatchAdmin(admin.ModelAdmin):
    """
    Every watched API. The schedule and the pause are changed through the two actions, so paused_reason and paused_at alwats move together. "Due now" is the quick way to try the runner: the watch is picked up at the next scheduled run.
    """

    list_display = (
        "target_url",
        "user",
        "state",
        "next_run_at",
        "last_run_at",
        "consecutive_failures",
    )
    list_filter = ("active", "paused_reason")
    search_fields = ("target_url", "user__email")
    list_select_related = ("user",)
    raw_id_fields = ("user", "domain", "last_scan")
    readonly_fields = (
        "target_key",
        "last_run_at",
        "last_scan",
        "consecutive_failures",
        "paused_reason",
        "paused_at",
        "created_at",
    )
    actions = ["make_due_now", "resume_selected"]

    @admin.display(description="state")
    def state(self, obj):
        if obj.is_paused:
            return f"paused: {obj.get_paused_reason_display().lower()}"
        if not obj.active:
            return "off"
        if not obj.user.watch_enabled:
            return "on (account switch off)"
        return "on"

    @admin.action(description="Due now (runs at the next scheduled run)")
    def make_due_now(self, request, queryset):
        count = queryset.update(next_run_at=timezone.now())
        self.message_user(request, f"{count} watch(es) due now.")

    @admin.action(description="Resume (clear the pause and the failure count)")
    def resume_selected(self, request, queryset):
        now = timezone.now()
        count = 0
        for watch in queryset:
            watch.resume(now=now)
            count += 1
        self.message_user(request, f"{count} watch(es) resumed.")