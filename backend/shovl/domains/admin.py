from django.contrib import admin

from .models import Domain


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """
    Every domain, verified or pending. Read-only: verification goes through the app, never
    by hand here. Deleting one also deletes its watches.
    """

    list_display = ("hostname", "user", "verified", "verification_method", "created_at", "verified_at")
    list_filter = ("verified", "verification_method")
    search_fields = ("hostname", "user__email")
    list_select_related = ("user",)
    readonly_fields = [field.name for field in Domain._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
