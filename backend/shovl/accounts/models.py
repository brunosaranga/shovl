import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

# ".invalid" is a reserved top-level domain, so a placeholder address can never belong to a real person or receive a real email.
GUEST_EMAIL_DOMAIN = "guest.shovl.invalid"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
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
    email         = models.EmailField(unique=True)
    is_active     = models.BooleanField(default=True)
    is_staff      = models.BooleanField(default=False)
    is_guest      = models.BooleanField(default=False)
    tos_agreed    = models.BooleanField(default=False)
    tos_agreed_at = models.DateTimeField(null=True, blank=True)
    date_joined   = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email