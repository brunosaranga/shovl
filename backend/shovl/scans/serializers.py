from rest_framework import serializers
from .models import Scan

class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = [
            "id",
            "target_url",
            "status",
            "verbose",
            "suggest_fix",
            "risk_score",
            "results",
            "pdf_path",
            "created_at",
            "completed_at",
        ]
        read_only_fields = [
            "status",
            "risk_score",
            "results",
            "pdf_path",
            "completed_at",
        ]