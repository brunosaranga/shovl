from rest_framework import serializers

from .models import Watch

class WatchSerializer(serializers.ModelSerializer):
    """
    
    One watched API, for Settings. in_plan comes from the view (context["in_plan], a set of ids from services.in_plan_ids), so the list costs one query for the plan, not one per row.
    
    """

    in_plan = serializers.SerializerMethodField()

    class Meta:
        model = Watch
        fields = [
            "id",
            "target_url",
            "active",
            "in_plan",
            "paused_reason",
            "next_run_at",
            "last_run_at",
            "last_scan",
            "activated_at",
        ]
        read_only_fields = fields

    def get_in_plan(self, watch):
        return watch.pk in self.context.get("in_plan", set())