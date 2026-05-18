from rest_framework import serializers

from media_source.models import MediaSource
from media_source.services.media_source_service import MediaSourceService


class MediaCredentials(serializers.Serializer):
    application_url = serializers.URLField()
    username = serializers.CharField()
    password = serializers.CharField()


class MediaSourceCreateSerializer(serializers.ModelSerializer):
    credentials = MediaCredentials()

    class Meta:
        model = MediaSource
        fields = ("id", "name", "credentials", "source_type",)

    def is_valid(self, *, raise_exception=False):
        is_valid = super().is_valid(raise_exception=raise_exception)
        if not is_valid:
            return is_valid

        media_source = MediaSource(
            name=self.validated_data["name"],
            credentials=self.validated_data["credentials"],
            source_type=self.validated_data["source_type"],
        )
        credentials_are_valid = MediaSourceService(media_source).check_credentials()
        if credentials_are_valid:
            return True

        self._errors.setdefault("credentials", []).append(
            "Impossible de se connecter a Jellyfin avec ces credentials."
        )
        if raise_exception:
            raise serializers.ValidationError(self.errors)
        return False

    def to_representation(self, instance):
        return MediaSourceSerializer().to_representation(instance)



class MediaSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaSource
        fields = ("id", "name", "credentials", "source_type", "analyzed_at", "analyze_status", "is_active")
