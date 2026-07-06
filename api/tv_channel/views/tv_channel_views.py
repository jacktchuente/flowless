from django.db import transaction
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from grid_schedule.models import PlayoutGenerationReport
from grid_schedule.serializers.playout_report_serializers import PlayoutGenerationReportSerializer
from tv_channel.models import GridBlock, TvChannel
from tv_channel.serializers.tv_channel_serializers import (
    TvChannelCreateSerializer,
    TvChannelDetailSerializer,
    TvChannelLogoUploadSerializer,
    TvChannelResetRulesSerializer,
    TvChannelSerializer,
    TvChannelUpdateSerializer,
)
from tv_channel.services.channel_name_suggestion_service import (
    ChannelNameSuggestionError,
    ChannelNameSuggestionService,
)
from tv_channel.services.logo_prompt_service import LogoPromptService
from tv_channel.tasks import generate_channel_editorial_line, generate_tv_channel_playout, push_tv_channel_to_etv


class TvChannelViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = TvChannelSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = TvChannel.objects.select_related("catalog", "editorialline").all()
        catalog_id = self.request.query_params.get("catalog")
        if catalog_id:
            queryset = queryset.filter(catalog_id=catalog_id)
        return queryset.order_by("name")

    def get_serializer_class(self):
        if self.action == "create":
            return TvChannelCreateSerializer
        if self.action in ("partial_update", "update"):
            return TvChannelUpdateSerializer
        if self.action == "retrieve":
            return TvChannelDetailSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=("post",), url_name="generate-blueprint", url_path="generate-blueprint")
    def generate_blueprint(self, request, pk=None):
        instance = self.get_object()
        reboot = str(request.data.get("reboot", "")).lower() in {"1", "true", "yes", "on"}
        raw_grid_only = request.data.get("grid_only", True)
        grid_only = str(raw_grid_only).lower() in {"1", "true", "yes", "on"}
        regenerate_editorial_line = not grid_only

        grid_generation_mode = request.data.get("grid_generation_mode")
        if not isinstance(grid_generation_mode, str) or not grid_generation_mode:
            use_preset = str(request.data.get("use_preset", "")).lower() in {"1", "true", "yes", "on"}
            if use_preset:
                grid_generation_mode = "preset_and_llm"
            else:
                grid_generation_mode = "full_llm"

        generate_channel_editorial_line.delay(
            instance.id,
            reboot=reboot,
            grid_generation_mode=grid_generation_mode,
            regenerate_editorial_line=regenerate_editorial_line,
        )
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=("post",), url_name="generate-playout", url_path="generate-playout")
    def generate_playout(self, request, pk=None):
        instance = self.get_object()
        days = int(request.data.get("days", 1))
        reset = str(request.data.get("reset", "")).lower() in {"1", "true", "yes", "on"}
        generate_tv_channel_playout.delay(
            instance.id,
            days=days,
            reset=reset,
        )
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=("post",), url_name="push", url_path="push")
    def push(self, request, pk=None):
        instance = self.get_object()
        push_tv_channel_to_etv.delay(instance.id)
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=("get",), url_name="generation-reports", url_path="generation-reports")
    def generation_reports(self, request, pk=None):
        instance = self.get_object()
        reports = (
            PlayoutGenerationReport.objects
            .filter(tv_playout__tv_channel=instance, tv_playout__is_active=True)
            .order_by("-created_at", "-id")[:10]
        )
        return Response(PlayoutGenerationReportSerializer(reports, many=True).data)

    @action(detail=True, methods=("post",), url_name="reset-rules", url_path="reset-rules")
    def reset_rules(self, request, pk=None):
        instance = self.get_object()
        serializer = TvChannelResetRulesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        type_to_suffix = {
            "category": "categories",
            "nature": "natures",
            "kind": "container_kinds",
        }
        levels = serializer.validated_data["levels"]
        types = serializer.validated_data["types"]
        fields_to_reset = [
            f"{level}_{type_to_suffix[item_type]}"
            for level in levels
            for item_type in types
        ]

        with transaction.atomic():
            editorial_line = getattr(instance, "editorialline", None)
            if editorial_line is not None:
                for field_name in fields_to_reset:
                    setattr(editorial_line, field_name, [])
                editorial_line.save(update_fields=[*fields_to_reset])

            blocks = list(
                GridBlock.objects
                .filter(grid_layout__tv_channel=instance)
            )
            for block in blocks:
                for field_name in fields_to_reset:
                    setattr(block, field_name, [])
            if blocks:
                GridBlock.objects.bulk_update(blocks, fields=fields_to_reset)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=("post",), url_name="suggest-name", url_path="suggest-name")
    def suggest_name(self, request, pk=None):
        instance = self.get_object()
        service = ChannelNameSuggestionService(instance)
        try:
            name = service.suggest_name()
        except ChannelNameSuggestionError as exc:
            return Response(
                status=status.HTTP_502_BAD_GATEWAY,
                data={"detail": str(exc)},
            )
        return Response({"name": name})

    @action(detail=True, methods=("post",), url_name="export-logo-prompt", url_path="export-logo-prompt")
    def export_logo_prompt(self, request, pk=None):
        instance = self.get_object()
        prompt = LogoPromptService(instance).generate_prompt()
        return Response({"prompt": prompt})

    @action(detail=True, methods=("post",), url_name="upload-logo", url_path="upload-logo")
    def upload_logo(self, request, pk=None):
        instance = self.get_object()
        serializer = TvChannelLogoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance.logo = serializer.validated_data["logo"]
        instance.save(update_fields=["logo", "updated_at"])
        return Response(TvChannelSerializer(instance, context=self.get_serializer_context()).data)
