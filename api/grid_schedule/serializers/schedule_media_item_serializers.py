from rest_framework import serializers

from grid_schedule.models import ScheduleMediaItem


class ScheduleMediaItemSerializer(serializers.ModelSerializer):
    media_item_title = serializers.CharField(source="item.title", read_only=True)
    media_item_description = serializers.CharField(source="item.description", read_only=True)
    media_container_title = serializers.CharField(source="item.container.title", read_only=True)
    media_container_id = serializers.IntegerField(source="item.container_id", read_only=True)
    block_name = serializers.SerializerMethodField()
    block_id = serializers.IntegerField(source="block_container_selection.block_id", read_only=True)

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
        )

    def get_block_name(self, obj) -> str:
        block = obj.block_container_selection.block
        return f"{block.starts_at.strftime('%H:%M')}-{block.ends_at.strftime('%H:%M')}"
