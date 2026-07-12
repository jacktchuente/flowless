from rest_framework import serializers

from media_source.models import MediaContainer


class MediaContainerSerializer(serializers.ModelSerializer):
    nature = serializers.IntegerField(source="media_collection.nature", read_only=True)
    container_kind = serializers.IntegerField(source="media_collection.container_kind", read_only=True)
    item_count = serializers.IntegerField(source="live_item_count", read_only=True)

    class Meta:
        model = MediaContainer
        fields = ("id", "title", "analyzed_at", "analyze_status", "item_count", "is_missing", "nature", "container_kind")


class MediaContainerDetailSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(source="live_item_count", read_only=True)

    class Meta:
        model = MediaContainer
        fields = ("id", "original_data_hash", "external_id", "title", "description", "media_source", "media_collection",
                  "analyzed_at", "analyze_status", "categories", "item_count", "duration_min_seconds",
                  "duration_max_seconds", "total_duration_seconds", "min_video_width", "min_video_height", "min_age",
                  "max_age", "release_date", "countries", "audio_languages", "subtitle_languages",
                  "audio_languages_any", "subtitle_languages_any", "overall_rating_score", "tags", "genres",
                  "is_missing",)
