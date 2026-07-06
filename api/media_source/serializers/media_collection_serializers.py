from rest_framework import serializers

from media_source.models import MediaCollection


class MediaCollectionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaCollection
        fields = ("id", "name", "is_active", "analyzed_at", "analyze_status", "programming_role", "nature", "container_kind", "is_anime")

    def to_representation(self, instance):
        return MediaCollectionSerializer().to_representation(instance)


class MediaCollectionSerializer(serializers.ModelSerializer):
    media_source_name = serializers.CharField(source="media_source.name", read_only=True)

    class Meta:
        model = MediaCollection
        fields = (
            "id",
            "name",
            "external_id",
            "media_source",
            "media_source_name",
            "is_active",
            "analyzed_at",
            "analyze_status",
            "programming_role",
            "nature",
            "container_kind",
            "is_anime",
        )
