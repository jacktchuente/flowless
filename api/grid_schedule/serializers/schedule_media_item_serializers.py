from rest_framework import serializers

from grid_schedule.models import ScheduleMediaItem
from media_source.constants import MediaProgrammingRole


class ScheduleMediaItemSerializer(serializers.ModelSerializer):
    media_item_title = serializers.CharField(source="item.title", read_only=True)
    media_item_description = serializers.CharField(source="item.description", read_only=True)
    media_container_title = serializers.CharField(source="item.container.title", read_only=True)
    media_container_id = serializers.IntegerField(source="item.container_id", read_only=True)
    block_name = serializers.SerializerMethodField()
    block_id = serializers.SerializerMethodField()
    flexible_selection_id = serializers.IntegerField(read_only=True)
    selection_type = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleMediaItem
        fields = (
            "id",
            "starts_at",
            "ends_at",
            "item",
            "media_item_title",
            "media_item_description",
            "media_container_id",
            "media_container_title",
            "block_id",
            "block_name",
            "flexible_selection_id",
            "selection_type",
            "role",
            "role_label",
            "parent_schedule_item",
        )

    def get_role_label(self, obj) -> str:
        return MediaProgrammingRole(obj.role).label

    def get_block_id(self, obj):
        if obj.block_container_selection_id:
            return obj.block_container_selection.block_id
        return None

    def get_block_name(self, obj) -> str:
        if not obj.block_container_selection_id:
            return "Flexible"
        block = obj.block_container_selection.block
        return f"{block.starts_at.strftime('%H:%M')}-{block.ends_at.strftime('%H:%M')}"

    def get_selection_type(self, obj) -> str:
        if obj.flexible_selection_id:
            return "flexible"
        return "fixed"
