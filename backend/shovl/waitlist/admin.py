from django.contrib import admin

from .models import WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    """
    The launch list, read-only. Entries come only through the site (double opt-in); "remove me"
    links and the daily cleanup delete them. The page title counts the confirmed ones: those are
    who send_launch_email writes to.
    """

    list_display = ("email", "first_name", "source", "confirmed", "agreed_at", "launch_sent_at")
    list_filter = ("source", ("confirmed_at", admin.EmptyFieldListFilter), ("launch_sent_at", admin.EmptyFieldListFilter))
    search_fields = ("email", "first_name")
    readonly_fields = [f.name for f in WaitlistEntry._meta.fields if f.name != "token_hash"]
    exclude = ("token_hash",)

    @admin.display(description="confirmed", boolean=True)
    def confirmed(self, obj):
        return obj.confirmed_at is not None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        confirmed = WaitlistEntry.objects.filter(confirmed_at__isnull=False).count()
        pending = WaitlistEntry.objects.filter(confirmed_at__isnull=True).count()
        extra_context = {**(extra_context or {}), "title": f"Launch list: {confirmed} confirmed, {pending} pending"}
        return super().changelist_view(request, extra_context=extra_context)
