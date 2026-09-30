from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .transfer import transfer_guest_scans

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "tos_agreed"]

    def validate_tos_agreed(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must agree to the terms of service to use shovl."
            )
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            tos_agreed=True,
            tos_agreed_at=timezone.now(),
        )
        return user


EMAIL_TAKEN_MESSAGE = "An account with this email already exists. Sign in instead."


class UpgradeSerializer(serializers.Serializer):
    """
    Turns a guest account into a registered one. The account keeps its id, so every scan already attached to it stays attached.

    The view passes the request in the serializer context, and calls upgrade(user) once is_valid() has passed.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    tos_agreed = serializers.BooleanField()

    def validate_tos_agreed(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must agree to the terms of service to use shovl."
            )
        return value

    def validate_email(self, value):
        value = User.objects.normalize_email(value.strip())
        guest = self.context["request"].user

        # Case sensitive, so "A@x.com" cannot slip past as existing "a@x.com".
        if User.objects.filter(email__iexact=value).exclude(pk=guest.pk).exists():
            raise serializers.ValidationError(EMAIL_TAKEN_MESSAGE)
        return value

    def upgrade(self, user):
        data = self.validated_data

        user.email = data["email"]
        user.set_password(data["password"])
        user.is_guest = False
        user.tos_agreed = True
        user.tos_agreed_at = timezone.now()

        try:
            with transaction.atomic():
                user.save(update_fields=[
                    "email", "password", "is_guest", "tos_agreed", "tos_agreed_at",
                ])
        except IntegrityError:
            # Someone else took the email between the check above and the save.
            raise serializers.ValidationError({"email": [EMAIL_TAKEN_MESSAGE]})

        return user


class LoginSerializer(TokenObtainPairSerializer):
    """
    Normal email + password sign-in, with one addition: if the request body also carries a `guest_token`, the scans of that guest are moved onto the account that just signed in, and the guest account is deleted.

    The guest token is read from the body, not the Authorization header, so an old or expired token can never get in the way of a normal sign-in.
    """

    def validate(self, attrs):
        # Checks the email and password. It raises on failure, so nothing below runs (and the guest is left alone) when the password is wrong.
        data = super().validate(attrs)

        # A missing, expired or unusable token just means nothing to transfer.
        transfer_guest_scans(self.initial_data_get('guest_token'), self.user)

        return data

