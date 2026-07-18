from rest_framework import serializers

from tv_channel.models import (
    ChannelImageEntityType,
    ChannelImageKind,
    ChannelImageSuggestion,
    ChannelImageSuggestionRun,
    TvChannel,
)


class ChannelImageSuggestionSerializer(serializers.ModelSerializer):
    thumbnail = serializers.FileField(read_only=True)

    class Meta:
        model = ChannelImageSuggestion
        fields = (
            "id",
            "position",
            "provider",
            "thumbnail",
            "width",
            "height",
            "attribution",
            "is_chosen",
        )


class ChannelImageSuggestionRunSerializer(serializers.ModelSerializer):
    suggestions = ChannelImageSuggestionSerializer(many=True, read_only=True)
    tv_channel_name = serializers.CharField(source="tv_channel.name", read_only=True)

    class Meta:
        model = ChannelImageSuggestionRun
        fields = (
            "id",
            "tv_channel",
            "tv_channel_name",
            "kind",
            "status",
            "entity_type",
            "query",
            "query_source",
            "diagnostics",
            "created_at",
            "updated_at",
            "suggestions",
        )


class ChannelImageSuggestionRunCreateSerializer(serializers.Serializer):
    tv_channel = serializers.PrimaryKeyRelatedField(queryset=TvChannel.objects.all())
    kind = serializers.ChoiceField(choices=ChannelImageKind.choices, default=ChannelImageKind.LOGO)
    query = serializers.CharField(max_length=255, required=False, allow_blank=True)
    entity_type = serializers.ChoiceField(
        choices=ChannelImageEntityType.choices, required=False, allow_blank=True
    )


class ChannelImageChooseSerializer(serializers.Serializer):
    suggestion_id = serializers.IntegerField()
