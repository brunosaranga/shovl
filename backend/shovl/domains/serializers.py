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

    def validate_hostname(self, value):
        value = value.strip().lower()

        if "/" in value or " " in value or "://" in value:
            raise serializers.ValidationError(
                "Enter a bare hostname, for example api.example.com"
            )

        # `user` is set in the view, not the serializer. so DRF's automatic unique_together check never runs. Without this a repeat submission reaches the database and comes back as a 500 instead of a clean 400.
        request = self.context.get("request")
        if request and Domain.objects.filter(user=request.user, hostname=value).exists():
            raise serializers.VAlidationError("You have already added this domain.")

        return value