from rest_framework import serializers

from tv_channel.models import GridBlock, GridLayout


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
            "allowed_categories",
            "forbidden_categories",
            "preferred_categories",
            "allowed_natures",
            "forbidden_natures",
            "preferred_natures",
            "allowed_container_kinds",
            "forbidden_container_kinds",
            "preferred_container_kinds",
            "post_filler_policy",
            "post_filler_policy_name",
        )


class GridSerializer(serializers.ModelSerializer):
    blocks = serializers.SerializerMethodField()

    class Meta:
        model = GridLayout
        fields = (
            "id",
            "created_at",
            "is_active",
            "mode",
            "post_filler_policy",
            "blocks",
        )

    def get_blocks(self, obj):
        queryset = obj.gridblock_set.all().order_by("starts_at", "id")
        return GridBlockSerializer(queryset, many=True).data
