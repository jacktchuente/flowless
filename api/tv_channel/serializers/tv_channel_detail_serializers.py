from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import serializers

from grid_schedule.models import PlayoutGenerationReport, ScheduleMediaItem, TvPlayout
from grid_schedule.serializers.playout_report_serializers import PlayoutGenerationReportSummarySerializer
from grid_schedule.serializers.schedule_media_item_serializers import ScheduleMediaItemSerializer
from tv_channel.models import TvChannel
from tv_channel.serializers.editorial_line_serializers import EditorialLineSerializer
from tv_channel.serializers.grid_serializers import GridSerializer


class TvChannelDetailSerializer(serializers.ModelSerializer):
    catalog_name = serializers.CharField(source="catalog.name", read_only=True)
    grid_data = serializers.SerializerMethodField()
    editorial_line_data = serializers.SerializerMethodField()
    active_schedule_items = serializers.SerializerMethodField()
    active_playout_id = serializers.SerializerMethodField()
    latest_generation_report = serializers.SerializerMethodField()
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
            "latest_generation_report",
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
        active_playout = self._get_active_playout(obj)
        if active_playout is None:
            return []

        queryset = (
            ScheduleMediaItem.objects
            .filter(
                Q(block_container_selection__tv_playout=active_playout)
                | Q(flexible_selection__tv_playout=active_playout)
                | Q(parent_schedule_item__block_container_selection__tv_playout=active_playout)
                | Q(parent_schedule_item__flexible_selection__tv_playout=active_playout)
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
        active_playout = self._get_active_playout(obj)
        return active_playout.id if active_playout is not None else None

    def get_latest_generation_report(self, obj):
        active_playout = self._get_active_playout(obj)
        if active_playout is None:
            return None
        report = (
            PlayoutGenerationReport.objects
            .filter(tv_playout=active_playout)
            .order_by("-created_at", "-id")
            .first()
        )
        if report is None:
            return None
        return PlayoutGenerationReportSummarySerializer(report).data

    def _get_active_playout(self, obj):
        active_playout = self.context.get("active_playout")
        if active_playout is not None:
            return active_playout

        active_playout = (
            TvPlayout.objects
            .filter(tv_channel=obj, is_active=True)
            .select_related("grid")
            .first()
        )
        self.context["active_playout"] = active_playout
        return active_playout
