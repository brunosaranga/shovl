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
        email = self.normalize_email(email)
        if not email:
            raise ValueError('Email is required')
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

    def clean(self):
        super().clean()
        # Lowercase before the admin's uniqueness checks run, so they compare like with like.
        self.email = UserManager.normalize_email(self.email)

    def save(self, *args, **kwargs):
        # Every path that stores an account ends here: the API, the manager and the admin.
        self.email = UserManager.normalize_email(self.email)
        super().save(*args, **kwargs)
