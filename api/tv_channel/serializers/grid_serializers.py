from rest_framework import serializers

from tv_channel.models import GridBlock, GridLayout
from tv_channel.serializers.marathon_serializers import MarathonKindPolicySerializer


class GridBlockSerializer(serializers.ModelSerializer):
    post_filler_policy_name = serializers.CharField(source="post_filler_policy.name", read_only=True)

    class Meta:
        model = GridBlock
        fields = (
            "id",
            "starts_at",
            "ends_at",
            "priority",
            "min_items",
            "max_items",
            "min_duration_seconds_per_item",
            "max_duration_seconds_per_item",
            "allowed",
            "preferred",
            "forbidden",
            "post_filler_policy",
            "post_filler_policy_name",
        )


class GridSerializer(serializers.ModelSerializer):
    blocks = serializers.SerializerMethodField()
    marathon_config = serializers.SerializerMethodField()

    class Meta:
        model = GridLayout
        fields = (
            "id",
            "created_at",
            "is_active",
            "mode",
            "post_filler_policy",
            "blocks",
            "marathon_config",
        )

    def get_blocks(self, obj):
        queryset = obj.gridblock_set.all().order_by("starts_at", "id")
        return GridBlockSerializer(queryset, many=True).data

    def get_marathon_config(self, obj):
        config = getattr(obj, "marathon_config", None)
        if config is None:
            return None
        return {
            "kind_policies": MarathonKindPolicySerializer(config.kind_policies.all(), many=True).data,
        }


class GridWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GridLayout
        fields = ("post_filler_policy",)
