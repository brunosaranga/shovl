from rest_framework import serializers
from .models import Domain

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = [
            "id",
            "hostname",
            "verified",
            "verification_token",
            "verification_method",
            "created_at",
            "verified_at",
        ]
        read_only_fields = [
            "verified",
            "verification_token",
            "verified_at",
        ]