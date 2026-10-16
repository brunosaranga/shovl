from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .tokens import TOKEN_VERSION_CLAIM
from .transfer import transfer_guest_scans

User = get_user_model()

# Hashing a huge "password" costs real CPU time, so the length is capped.
PASSWORD_MAX_LENGTH = 128

EMAIL_TAKEN_MESSAGE = "An account with this email already exists. Sign in instead."


def check_password_strength(password, email):
    """
    Apply the validators in AUTH_PASSWORD_VALIDATORS (length, common passwords,
    all-numeric, too similar to the email). Every problem is reported at once,
    as a 400 with {"password": [message, ...]}.

    Used when a password is chosen (register, upgrade), never when signing in:
    an existing password that would fail today must still be able to log in.
    """
    try:
        validate_password(password, user=User(email=email))
    except DjangoValidationError as e:
        raise serializers.ValidationError({"password": list(e.messages)})


class RegisterSerializer(serializers.ModelSerializer):
    # Declared here instead of taken from the model, so the uniqueness check below
    # (case-insensitive) replaces DRF's automatic one (exact match only).
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=PASSWORD_MAX_LENGTH)

    class Meta:
        model = User
        fields = ["email", "password", "tos_agreed"]

    def validate_email(self, value):
        value = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(EMAIL_TAKEN_MESSAGE)
        return value

    def validate_tos_agreed(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must agree to the terms of service to use shovl."
            )
        return value

    def validate(self, attrs):
        check_password_strength(attrs["password"], attrs.get("email"))
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=validated_data["email"],
                    password=validated_data["password"],
                    tos_agreed=True,
                    tos_agreed_at=timezone.now(),
                )
        except IntegrityError:
            # Someone registered the same address between the check above and the save.
            raise serializers.ValidationError({"email": [EMAIL_TAKEN_MESSAGE]})


class UpgradeSerializer(serializers.Serializer):
    """
    Turns a guest account into a registered one. The account keeps its id, so every scan already attached to it stays attached.

    The view passes the request in the serializer context, and calls upgrade(user) once is_valid() has passed.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=PASSWORD_MAX_LENGTH)
    tos_agreed = serializers.BooleanField()

    def validate_tos_agreed(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must agree to the terms of service to use shovl."
            )
        return value

    def validate_email(self, value):
        # Trimmed and lowercased (see UserManager.normalize_email).
        value = User.objects.normalize_email(value)
        guest = self.context["request"].user

        # Case-insensitive, so "A@x.com" cannot slip past an existing "a@x.com".
        if User.objects.filter(email__iexact=value).exclude(pk=guest.pk).exists():
            raise serializers.ValidationError(EMAIL_TAKEN_MESSAGE)
        return value

    def validate(self, attrs):
        # The new email, not the guest's placeholder, is what the password is compared with.
        check_password_strength(attrs["password"], attrs["email"])
        return attrs

    def upgrade(self, user):
        data = self.validated_data

        user.email = data["email"]
        user.set_password(data["password"])
        user.is_guest = False
        user.tos_agreed = True
        user.tos_agreed_at = timezone.now()
        # Signs out the guest token (and any copy of it). The view then issues a
        # fresh pair carrying the new version.
        user.token_version += 1

        try:
            with transaction.atomic():
                user.save(update_fields=[
                    "email", "password", "is_guest", "tos_agreed", "tos_agreed_at",
                    "token_version",
                ])
        except IntegrityError:
            # Someone else took the email between the check above and the save.
            raise serializers.ValidationError({"email": [EMAIL_TAKEN_MESSAGE]})

        return user


class LoginSerializer(TokenObtainPairSerializer):
    """
    Normal email + password sign-in, with one addition: if the request body also carries a `guest_token`, the scans of that guest are moved onto the account that just signed in, and the guest account is deleted.

    The guest token is read from the body, not the Authorization header, so an old or expired token can never get in the way of a normal sign-in.

    The email can be typed in any case: the lookup goes through UserManager.get_by_natural_key, which lowercases it.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token[TOKEN_VERSION_CLAIM] = user.token_version
        return token

    def validate(self, attrs):
        # Checks the email and password. It raises on failure, so nothing below runs (and the guest is left alone) when the password is wrong.
        data = super().validate(attrs)

        # A missing, expired or unusable token just means nothing to transfer.
        transfer_guest_scans(self.initial_data.get('guest_token'), self.user)

        return data
