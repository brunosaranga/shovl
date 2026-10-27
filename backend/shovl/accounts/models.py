import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

# ".invalid" is a reserved top-level domain, so a placeholder address can never belong to a real person or receive a real email.
GUEST_EMAIL_DOMAIN = "guest.xikomu.invalid"


class UserManager(BaseUserManager):
    @classmethod
    def normalize_email(cls, email):
        """
        The whole address, trimmed and lowercased. Django's own version only lowercases the domain, which let Bruno@x.com and bruno@x.com become two accounts.
        """
        return (email or "").strip().lower()

    def get_by_natural_key(self, username):
        # Every sign-in (the API and the admin) looks the account up here, so an address typed in any case finds it.
        return self.get(**{self.model.USERNAME_FIELD: self.normalize_email(username)})

    def create_user(self, email, password=None, **extra_fields):
        """
        Accounts made here count as confirmed (email_confirmed_at = now), because this is
        trusted code: createsuperuser, the shell, tests. The two ways in from the internet
        say otherwise explicitly: sign-up (accounts/serializers.py) passes
        email_confirmed_at=None, and guests are never confirmed.
        """
        email = self.normalize_email(email)
        if not email:
            raise ValueError('Email is required')
        if extra_fields.get("is_guest"):
            extra_fields["email_confirmed_at"] = None
        else:
            extra_fields.setdefault("email_confirmed_at", timezone.now())
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

    def create_guest(self, **extra_fields):
        """
        Create a guest account: a random placeholder email and no usable password. The caller is responsible for checking consent first and passing tos_agreed / tos_agreed_at through extra_fields.
        """
        email = f"guest-{uuid.uuid4().hex}@{GUEST_EMAIL_DOMAIN}"
        return self.create_user(email, password=None, is_guest=True, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    PLAN_FREE = "free"
    PLAN_PRO = "pro"
    PLAN_CHOICES = [
        (PLAN_FREE, "Free"),
        (PLAN_PRO, "Pro"),
    ]

    email         = models.EmailField(unique=True)
    is_active     = models.BooleanField(default=True)
    is_staff      = models.BooleanField(default=False)
    is_guest      = models.BooleanField(default=False)
    # Raising this signs out every token the account has ever been given (see accounts/tokens.py).
    token_version = models.PositiveIntegerField(default=0)
    tos_agreed    = models.BooleanField(default=False)
    tos_agreed_at = models.DateTimeField(null=True, blank=True)
    date_joined   = models.DateTimeField(default=timezone.now)

    # When the owner proved the address is theirs, by typing the code xikomu emailed to it
    # (accounts/confirmation.py). Empty: not confirmed yet. Until then the account can't add or
    # scan its own domains, use murindzi or change settings (accounts/permissions.py), and the
    # only email it gets is the code.
    email_confirmed_at = models.DateTimeField(null=True, blank=True)
    # An account that signs up (or turns a guest into an account) must confirm by then, or the
    # daily cleanup deletes it (purge_guests), which frees an address someone took without
    # owning it. Empty for accounts that existed before confirmation did: they confirm at their
    # next visit and are never deleted for it. Cleared once confirmed.
    confirm_by = models.DateTimeField(null=True, blank=True)

    # What the account signed up for. What it gets right now is accounts/plans.py's
    # effective_plan(), which also looks at billing: never read this field to decide a feature.
    plan = models.CharField(
        max_length=10,
        choices=PLAN_CHOICES,
        default=PLAN_FREE,
        help_text="What the account signed up for. Set by hand until billing exists.",
    )
    # Settings > murindzi. Off pauses every watch; nothing is deleted, and no new watch
    # starts while it is off.
    watch_enabled = models.BooleanField(
        default=True,
        help_text="murindzi on or off for the whole account.",
    )
    # The bell's mute. Scheduled scans still run and alerts still land in the list, but the
    # badge (and, later, email) stays quiet. Items that need action are never muted.
    notifications_muted = models.BooleanField(default=False)
    # Set once, the first time the account gets a watch, when the "murindzi is on"
    # notification goes out. Never cleared, so the announcement never repeats.
    watch_intro_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            # The database-level backstop for the lowercasing in save(): two addresses that differ only in case can never both be stored, whatever path the write takes.
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
                violation_error_message="An account with this email already exists.",
            ),
        ]

    def __str__(self):
        return self.email

    @property
    def email_confirmed(self):
        return self.email_confirmed_at is not None

    def clean(self):
        super().clean()
        # Lowercase before the admin's uniqueness checks run, so they compare like with like.
        self.email = UserManager.normalize_email(self.email)

    def save(self, *args, **kwargs):
        # Every path that stores an account ends here: the API, the manager and the admin.
        self.email = UserManager.normalize_email(self.email)
        super().save(*args, **kwargs)


class EmailCode(models.Model):
    """
    A 6-digit code emailed to an account (accounts/confirmation.py). Only the newest code of a
    purpose works, and only for the address it was sent to. Stored as a keyed hash, never the
    digits. Deleted when it's used, replaced, or by the daily cleanup once expired.

    Password reset (a later step) will add its own purpose here.
    """

    PURPOSE_CONFIRM = "confirm"
    PURPOSE_CHOICES = [
        (PURPOSE_CONFIRM, "confirm email"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_codes")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    # mailer.services.address_hash() of the address the code went to: a code sent before the
    # address changed doesn't confirm the new one.
    sent_to = models.CharField(max_length=64)
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["user", "purpose", "-created_at"], name="emailcode_user_purpose"),
        ]

    def __str__(self):
        return f"{self.get_purpose_display()} code for account {self.user_id}"
