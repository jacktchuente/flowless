from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from grid_schedule.models import ScheduleMediaItem, TvPlayout
from grid_schedule.serializers.schedule_media_item_serializers import ScheduleMediaItemSerializer
from tv_channel.models import TvChannel
from tv_channel.serializers.editorial_line_serializers import EditorialLineSerializer
from tv_channel.serializers.grid_serializers import GridSerializer
from tv_channel.serializers.tv_channel_detail_serializers import TvChannelDetailSerializer


class TvChannelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TvChannel
        fields = ("id", "name", "description", "specification", "catalog")

    def to_representation(self, instance):
        return TvChannelSerializer().to_representation(instance)


class TvChannelUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TvChannel
        fields = ("id", "name", "description", "specification", "catalog", "is_enabled")

    def to_representation(self, instance):
        return TvChannelSerializer().to_representation(instance)


class TvChannelSerializer(serializers.ModelSerializer):
    catalog_name = serializers.CharField(source="catalog.name", read_only=True)
    grid_data = serializers.SerializerMethodField()
    editorial_line_data = serializers.SerializerMethodField()
    active_schedule_items = serializers.SerializerMethodField()
    active_playout_id = serializers.SerializerMethodField()
    logo = serializers.FileField(read_only=True)

    class Meta:
        model = TvChannel
        fields = (
            "id",
            "name",
            "description",
            "specification",
            "analyze_status",
            "catalog",
            "catalog_name",
            "is_enabled",
            "external_playout_id",
            "logo",
            "created_at",
            "updated_at",
            "grid_data",
            "editorial_line_data",
            "active_schedule_items",
            "active_playout_id",
        )

    def get_grid_data(self, obj):
        active_grid = (
            obj.gridlayout_set
            .filter(is_active=True)
            .order_by("-created_at", "-id")
            .first()
        )
        if active_grid is None:
            return None
        return GridSerializer(active_grid).data

    def get_editorial_line_data(self, obj):
        try:
            editorial_line = obj.editorialline
        except ObjectDoesNotExist:
            return None
        return EditorialLineSerializer(editorial_line).data

    def get_active_schedule_items(self, obj):
        now = timezone.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        queryset = (
            ScheduleMediaItem.objects
            .filter(
                (
                    Q(block_container_selection__tv_playout__tv_channel=obj)
                    & Q(block_container_selection__tv_playout__is_active=True)
                )
                | (
                    Q(flexible_selection__tv_playout__tv_channel=obj)
                    & Q(flexible_selection__tv_playout__is_active=True)
                )
                | (
                    Q(parent_schedule_item__block_container_selection__tv_playout__tv_channel=obj)
                    & Q(parent_schedule_item__block_container_selection__tv_playout__is_active=True)
                )
                | (
                    Q(parent_schedule_item__flexible_selection__tv_playout__tv_channel=obj)
                    & Q(parent_schedule_item__flexible_selection__tv_playout__is_active=True)
                ),
                starts_at__lt=day_end,
                ends_at__gt=day_start,
            )
            .select_related(
                "item",
                "item__container",
                "block_container_selection__block",
                "flexible_selection",
            )
            .order_by("starts_at")
        )
        return ScheduleMediaItemSerializer(queryset, many=True).data

    def get_active_playout_id(self, obj):
        active_playout = (
            TvPlayout.objects
            .filter(tv_channel=obj, is_active=True)
            .only("id")
            .first()
        )
        return active_playout.id if active_playout is not None else None


class TvChannelResetRulesSerializer(serializers.Serializer):
    TYPE_CATEGORY = "category"
    TYPE_NATURE = "nature"
    TYPE_KIND = "kind"
    LEVEL_ALLOWED = "allowed"
    LEVEL_FORBIDDEN = "forbidden"

    types = serializers.ListField(
        child=serializers.ChoiceField(choices=(TYPE_CATEGORY, TYPE_NATURE, TYPE_KIND)),
        allow_empty=False,
    )
    levels = serializers.ListField(
        child=serializers.ChoiceField(choices=(LEVEL_ALLOWED, LEVEL_FORBIDDEN)),
        allow_empty=False,
    )

    def validate_types(self, value):
        return list(dict.fromkeys(value))

    def validate_levels(self, value):
        return list(dict.fromkeys(value))


class TvChannelLogoUploadSerializer(serializers.Serializer):
    logo = serializers.FileField()


__all__ = [
    "TvChannelCreateSerializer",
    "TvChannelDetailSerializer",
    "TvChannelLogoUploadSerializer",
    "TvChannelResetRulesSerializer",
    "TvChannelSerializer",
    "TvChannelUpdateSerializer",
]
