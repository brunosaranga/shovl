from django.contrib import admin, messages
from django.utils import timezone

from .models import EmailCode, User
from .plans import effective_plan


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Accounts, mainly to hand out Pro by hand until billing exists ("plan"). "Gets" is what the
    account actually receives right now (accounts/plans.py), which is what every feature uses.

    Accounts are created through the app, never here, and the email, password and staff flag
    can't be changed from this page: those go through createsuperuser or the shell.

    "Confirmed" is when the owner typed the code emailed to them (accounts/confirmation.py).
    The action "Mark email as confirmed" is for support: someone who proved the address another
    way, for example by writing to support@ from it, while email sending is down.
    """

    list_display = ("email", "plan", "gets", "is_guest", "confirmed", "watch_enabled", "date_joined")
    list_filter = (
        "plan",
        "is_guest",
        ("email_confirmed_at", admin.EmptyFieldListFilter),
        "is_staff",
        "watch_enabled",
    )
    actions = ["mark_confirmed"]
    search_fields = ("email",)
    ordering = ("-date_joined",)
    fields = (
        "email",
        "plan",
        "gets",
        "watch_enabled",
        "notifications_muted",
        "email_alerts",
        "watch_intro_at",
        "is_active",
        "is_guest",
        "is_staff",
        "date_joined",
        "tos_agreed_at",
        "email_confirmed_at",
        "confirm_by",
    )
    readonly_fields = (
        "email",
        "gets",
        "watch_intro_at",
        "is_guest",
        "is_staff",
        "date_joined",
        "tos_agreed_at",
        "email_confirmed_at",
        "confirm_by",
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="gets")
    def gets(self, obj):
        return effective_plan(obj).name

    @admin.display(description="confirmed", boolean=True)
    def confirmed(self, obj):
        if obj.is_guest:
            return None
        return obj.email_confirmed_at is not None

    @admin.action(description="Mark email as confirmed")
    def mark_confirmed(self, request, queryset):
        accounts = queryset.filter(is_guest=False, email_confirmed_at__isnull=True)
        ids = list(accounts.values_list("pk", flat=True))
        updated = User.objects.filter(pk__in=ids).update(
            email_confirmed_at=timezone.now(), confirm_by=None
        )
        EmailCode.objects.filter(user__in=ids, purpose=EmailCode.PURPOSE_CONFIRM).delete()
        from waitlist.services import account_confirmed

        for user in User.objects.filter(pk__in=ids):
            account_confirmed(user)
        self.message_user(request, f"{updated} account(s) marked as confirmed.", messages.SUCCESS)
