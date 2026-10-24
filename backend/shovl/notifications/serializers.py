from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "kind",
            "title",
            "summary",
            "data",
            "watch",
            "scan",
            "read",
            "created_at",
        ]
        read_only_fields = fields

    def get_read(self, notification):
        return notification.read_at is not None
