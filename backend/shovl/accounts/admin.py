from django.contrib import admin

from .models import User
from .plans import effective_plan


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Accounts, mainly to hand out Pro by hand until billing exists ("plan"). "Gets" is what the
    account actually receives right now (accounts/plans.py), which is what every feature uses.

    Accounts are created through the app, never here, and the email, password and staff flag
    can't be changed from this page: those go through createsuperuser or the shell.
    """

    list_display = ("email", "plan", "gets", "is_guest", "watch_enabled", "date_joined")
    list_filter = ("plan", "is_guest", "is_staff", "watch_enabled")
    search_fields = ("email",)
    ordering = ("-date_joined",)
    fields = (
        "email",
        "plan",
        "gets",
        "watch_enabled",
        "notifications_muted",
        "watch_intro_at",
        "is_active",
        "is_guest",
        "is_staff",
        "date_joined",
        "tos_agreed_at",
    )
    readonly_fields = (
        "email",
        "gets",
        "watch_intro_at",
        "is_guest",
        "is_staff",
        "date_joined",
        "tos_agreed_at",
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="gets")
    def gets(self, obj):
        return effective_plan(obj).name
