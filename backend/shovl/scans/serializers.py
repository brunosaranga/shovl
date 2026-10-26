import re

from rest_framework import serializers

from watch.services import scan_watch_state

from .compare import comparison_for
from .models import Scan, ScanFeedback


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
            "trigger",
            "created_at",
            "completed_at",
        ]
        read_only_fields = [
            "status",
            "risk_score",
            "results",
            "pdf_path",
            "trigger",
            "completed_at",
        ]


class ScanDetailSerializer(ScanSerializer):
    """
    One scan, for the report page (GET /api/scans/<id>/). Adds what only the report shows:
      comparison  "since your last scan" (scans/compare.py), or null when there is nothing to
                  compare with or the scan did not complete
      feedback    the answer to "was this report useful?", or null
      watch       murindzi's badge for this scan's API (watch/services.py, scan_watch_state),
                  or null for practice targets and guests
    The list endpoint leaves all three out: they cost a query or two per scan.
    """

    comparison = serializers.SerializerMethodField()
    feedback = serializers.SerializerMethodField()
    watch = serializers.SerializerMethodField()

    class Meta(ScanSerializer.Meta):
        fields = ScanSerializer.Meta.fields + ["comparison", "feedback", "watch"]

    def get_watch(self, scan):
        return scan_watch_state(scan)

    def get_comparison(self, scan):
        return comparison_for(scan)

    def get_feedback(self, scan):
        answer = ScanFeedback.objects.filter(scan=scan).first()
        return FeedbackSerializer(answer).data if answer else None


# Control characters other than tab and newline. NUL above all: Postgres cannot store it.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class FeedbackSerializer(serializers.Serializer):
    """
    POST /api/scans/<id>/feedback/. Every field is optional on its own, but the first answer
    for a scan must say whether the report was useful (the view checks that).
    """

    useful = serializers.BooleanField(required=False)
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        max_length=ScanFeedback.COMMENT_MAX_LENGTH,
        error_messages={
            "max_length": f"Keep it under {ScanFeedback.COMMENT_MAX_LENGTH} characters.",
        },
    )
    would_pay = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=[value for value, _ in ScanFeedback.WOULD_PAY_CHOICES],
    )

    def validate_comment(self, value):
        value = _CONTROL.sub("", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise serializers.ValidationError("That comment contains characters that can't be saved.")
        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Send useful, comment or would_pay.")
        return attrs
