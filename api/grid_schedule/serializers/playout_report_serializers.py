from rest_framework import serializers

from grid_schedule.models import PlayoutGenerationReport


class PlayoutGenerationReportSerializer(serializers.ModelSerializer):
    issue_counts = serializers.SerializerMethodField()

    class Meta:
        model = PlayoutGenerationReport
        fields = (
            "id",
            "tv_playout",
            "created_at",
            "trigger",
            "window_start",
            "window_end",
            "generated_items",
            "filled_items",
            "repaired_gaps",
            "trimmed_overlaps",
            "issues",
            "issue_counts",
        )

    def get_issue_counts(self, obj) -> dict:
        counts = {"error": 0, "warning": 0, "info": 0}
        for issue in obj.issues or []:
            severity = issue.get("severity")
            if severity in counts:
                counts[severity] += 1
        return counts


class PlayoutGenerationReportSummarySerializer(PlayoutGenerationReportSerializer):
    class Meta(PlayoutGenerationReportSerializer.Meta):
        fields = (
            "id",
            "created_at",
            "trigger",
            "generated_items",
            "filled_items",
            "repaired_gaps",
            "trimmed_overlaps",
            "issue_counts",
        )
