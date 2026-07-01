from rest_framework import serializers

from editorial_planning.models import (
    EditorialChannelCandidate,
    EditorialChannelSegment,
    EditorialFlowRun,
    EditorialPlannedGrid,
    EditorialSegment,
    EditorialSegmentPath,
    EditorialSegmentPathElement,
)


class EditorialPlanningGenerationRequestSerializer(serializers.Serializer):
    media_collection_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    max_channel_candidates = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    target_channel_count = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    def validate_media_collection_ids(self, value):
        return list(dict.fromkeys(value))


class EditorialFlexibleChannelCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=50)


class EditorialSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialSegment
        fields = (
            "id",
            "segment_key",
            "name",
            "description",
            "profile",
            "programmable_score",
            "cohesion_score",
            "separation_score",
            "format_consistency_score",
            "volume_score",
            "labelability_score",
            "acceptance_threshold",
            "media_count",
        )


class EditorialChannelSegmentSerializer(serializers.ModelSerializer):
    segment_name = serializers.CharField(source="segment.name", read_only=True)

    class Meta:
        model = EditorialChannelSegment
        fields = (
            "id",
            "segment",
            "segment_name",
            "role",
            "weight",
            "position",
        )


class EditorialSegmentPathElementSerializer(serializers.ModelSerializer):
    segment_name = serializers.CharField(source="segment.name", read_only=True)

    class Meta:
        model = EditorialSegmentPathElement
        fields = (
            "id",
            "segment",
            "segment_name",
            "position",
            "role",
            "reason",
            "transition_from_previous_score",
        )


class EditorialSegmentPathSerializer(serializers.ModelSerializer):
    elements = EditorialSegmentPathElementSerializer(many=True, read_only=True)

    class Meta:
        model = EditorialSegmentPath
        fields = (
            "id",
            "is_loop",
            "global_score",
            "diagnostics",
            "elements",
        )


class EditorialPlannedGridSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialPlannedGrid
        fields = (
            "id",
            "grid_layout",
            "created_at",
            "updated_at",
        )


class EditorialChannelCandidateSerializer(serializers.ModelSerializer):
    channel_segments = EditorialChannelSegmentSerializer(many=True, read_only=True)
    segment_path = EditorialSegmentPathSerializer(read_only=True)
    planned_grid = EditorialPlannedGridSerializer(read_only=True)
    tv_channel_name = serializers.CharField(source="tv_channel.name", read_only=True)

    class Meta:
        model = EditorialChannelCandidate
        fields = (
            "id",
            "channel_key",
            "tv_channel",
            "tv_channel_name",
            "name",
            "description",
            "viability_score",
            "status",
            "profile",
            "diagnostics",
            "channel_segments",
            "segment_path",
            "planned_grid",
            "created_at",
            "updated_at",
        )


class EditorialFlowRunSerializer(serializers.ModelSerializer):
    channel_candidates = EditorialChannelCandidateSerializer(many=True, read_only=True)

    class Meta:
        model = EditorialFlowRun
        fields = (
            "id",
            "catalog",
            "status",
            "is_active",
            "algorithm_version",
            "config",
            "diagnostics",
            "source_media_count",
            "segment_count",
            "channel_candidate_count",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "channel_candidates",
        )
