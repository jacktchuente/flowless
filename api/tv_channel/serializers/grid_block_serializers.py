from tv_channel.models import GridBlock
from rest_framework import serializers


class GridBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = GridBlock
        fields = ("id", "grid_layout", "starts_at", "ends_at", "priority", "min_items", "max_items",
                  "min_duration_seconds_per_item", "max_duration_seconds_per_item", "allowed_categories",
                  "forbidden_categories", "preferred_categories", "allowed_natures", "forbidden_natures",
                  "preferred_natures", "allowed_container_kinds", "forbidden_container_kinds",
                  "preferred_container_kinds", "post_filler_policy",)
