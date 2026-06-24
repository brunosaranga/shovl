from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

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