from django.db import transaction
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from grid_schedule.models import PlayoutGenerationReport
from grid_schedule.serializers.playout_report_serializers import PlayoutGenerationReportSerializer
from django.utils.timezone import now
from media_source.constants import MediaContainerKind, MediaNature, MediaProgrammingRole
from rule_engine.services import category_service, vocabulary_service
from tv_channel.models import (
    EditorialLine,
    FillerPolicy,
    GridBlock,
    GridLayout,
    GridLayoutMode,
    MarathonConfig,
    MarathonKindPolicy,
    TvChannel,
)
from tv_channel.serializers.editorial_line_serializers import EditorialLineSerializer, EditorialLineWriteSerializer
from tv_channel.serializers.form_suggestion_serializers import FormSuggestionRequestSerializer
from tv_channel.serializers.grid_serializers import GridSerializer, GridWriteSerializer
from tv_channel.serializers.marathon_serializers import MarathonConfigWriteSerializer, MarathonKindPolicySerializer
from tv_channel.services.grid_editing import GridNotEditableError, compute_grid_warnings, get_editable_grid_layout
from tv_channel.services.image_suggestion.query_service import ChannelImageQueryService
from tv_channel.services.form_suggestion_service import FormSuggestionError, FormSuggestionService
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
from tv_channel.services.logo_generation.logo_generation_service import BACKENDS as LOGO_BACKENDS
from tv_channel.services.logo_prompt_service import LogoPromptService
from tv_channel.tasks import (
    generate_channel_editorial_line,
    generate_tv_channel_logo,
    generate_tv_channel_playout,
    push_tv_channel_to_etv,
)


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

    @action(detail=False, methods=("get",), url_path="form-options")
    def form_options(self, request):
        return Response({
            "categories": category_service.get_all_category_names(),
            "natures": [{"value": choice.value, "label": choice.label} for choice in MediaNature],
            "container_kinds": [{"value": choice.value, "label": choice.label} for choice in MediaContainerKind],
            "programming_roles": [{"value": choice.value, "label": choice.label} for choice in MediaProgrammingRole],
            "filler_policies": list(FillerPolicy.objects.order_by("name").values("id", "name", "duration_seconds")),
        })

    @action(detail=False, methods=("get",), url_path="rule-option-search")
    def rule_option_search(self, request):
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return Response({"results": []})
        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 50))
        return Response({"results": vocabulary_service.search(query, limit=limit)})

    @action(detail=True, methods=("get", "put", "patch"), url_path="editorial-line")
    def editorial_line(self, request, pk=None):
        channel = self.get_object()
        if request.method == "GET":
            line = getattr(channel, "editorialline", None)
            if line is None:
                return Response({"detail": "Editorial line not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response(EditorialLineSerializer(line).data)
        line, _ = EditorialLine.objects.get_or_create(tv_channel=channel)
        serializer = EditorialLineWriteSerializer(
            line, data=request.data, partial=request.method == "PATCH"
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EditorialLineSerializer(line).data)

    @action(detail=True, methods=("patch",), url_path="grid")
    def grid(self, request, pk=None):
        try:
            layout = get_editable_grid_layout(self.get_object())
        except GridNotEditableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GridWriteSerializer(layout, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(GridSerializer(layout).data)

    @action(detail=True, methods=("post",), url_path="grid/new-version")
    def new_grid_version(self, request, pk=None):
        channel = self.get_object()
        try:
            source = get_editable_grid_layout(channel)
        except GridNotEditableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            source.is_active = False
            source.save(update_fields=["is_active"])
            copy = GridLayout.objects.create(
                tv_channel=channel, mode=source.mode, post_filler_policy=source.post_filler_policy,
                is_active=True, created_at=now(),
            )
            fields = [field.name for field in GridBlock._meta.fields if field.name not in ("id", "grid_layout")]
            GridBlock.objects.bulk_create([
                GridBlock(grid_layout=copy, **{field: getattr(block, field) for field in fields})
                for block in source.gridblock_set.all()
            ])
            source_config = getattr(source, "marathon_config", None)
            if source_config is not None:
                copy_config = MarathonConfig.objects.create(grid_layout=copy)
                MarathonKindPolicy.objects.bulk_create([
                    MarathonKindPolicy(
                        config=copy_config,
                        container_kind=policy.container_kind,
                        min_run=policy.min_run,
                        max_run=policy.max_run,
                        quota=policy.quota,
                    )
                    for policy in source_config.kind_policies.all()
                ])
        return Response(GridSerializer(copy).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("get",), url_path="image-query-preview")
    def image_query_preview(self, request, pk=None):
        # Requete deterministe (axes edito seulement, jamais de LLM ici)
        # pour preremplir le champ editable de la page Images.
        channel = self.get_object()
        image_query = ChannelImageQueryService(channel).resolve_from_axes()
        if image_query is None:
            return Response({"entity_type": None, "query": None, "source": None})
        return Response({
            "entity_type": image_query.entity_type,
            "query": image_query.query,
            "source": image_query.source,
        })

    @action(detail=True, methods=("get", "put"), url_path="marathon-config")
    def marathon_config(self, request, pk=None):
        channel = self.get_object()
        layout = (
            channel.gridlayout_set.filter(is_active=True)
            .order_by("-created_at", "-id")
            .first()
        )
        if layout is None or layout.mode != GridLayoutMode.MARATHON:
            return Response(
                {"detail": "Channel has no active marathon grid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        config = getattr(layout, "marathon_config", None)

        if request.method == "GET":
            policies = config.kind_policies.all() if config is not None else []
            return Response({"kind_policies": MarathonKindPolicySerializer(policies, many=True).data})

        serializer = MarathonConfigWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            if config is None:
                config = MarathonConfig.objects.create(grid_layout=layout)
            # Remplacement complet: ce qui n'est pas dans le payload disparait.
            config.kind_policies.all().delete()
            MarathonKindPolicy.objects.bulk_create([
                MarathonKindPolicy(config=config, **policy)
                for policy in serializer.validated_data["kind_policies"]
            ])
        return Response({"kind_policies": MarathonKindPolicySerializer(config.kind_policies.all(), many=True).data})

    @action(detail=True, methods=("get",), url_path="grid-warnings")
    def grid_warnings(self, request, pk=None):
        channel = self.get_object()
        layout = channel.gridlayout_set.filter(is_active=True).first()
        if layout is None or layout.mode != GridLayoutMode.FIXED:
            return Response({"warnings": []})
        return Response({"warnings": compute_grid_warnings(layout)})

    @action(detail=True, methods=("post",), url_path="suggest-form")
    def suggest_form(self, request, pk=None):
        channel = self.get_object()
        serializer = FormSuggestionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["form_kind"] in ("grid", "grid_block"):
            try:
                get_editable_grid_layout(channel)
            except GridNotEditableError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        block = None
        if "grid_block_id" in data:
            block = GridBlock.objects.filter(pk=data["grid_block_id"], grid_layout__tv_channel=channel).first()
            if block is None:
                return Response({"grid_block_id": "Block does not belong to this channel."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            values = FormSuggestionService(
                channel, data["form_kind"], data["user_context"], data["current_values"], block
            ).suggest()
        except FormSuggestionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"values": values})

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

    @action(detail=True, methods=("post",), url_name="generate-logo", url_path="generate-logo")
    def generate_logo(self, request, pk=None):
        instance = self.get_object()
        backend = request.data.get("backend")
        if backend is not None:
            backend = str(backend).strip().lower()
            if backend not in LOGO_BACKENDS:
                return Response(
                    {"backend": f"Unknown backend. Available: {', '.join(sorted(LOGO_BACKENDS))}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        generate_tv_channel_logo.delay(instance.id, backend=backend)
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

        type_to_axis = {
            "category": "categories",
            "nature": "natures",
            "kind": "container_kinds",
            "director": "directors",
            "writer": "writers",
            "creator": "creators",
            "actor": "actors",
            "studio": "studios",
            "country": "countries",
            "audio_language": "audio_languages",
            "subtitle_language": "subtitle_languages",
        }
        levels = serializer.validated_data["levels"]
        axes = [type_to_axis[item_type] for item_type in serializer.validated_data["types"]]

        def reset_rule_axes(target):
            for level in levels:
                rules = dict(getattr(target, level) or {})
                for axis in axes:
                    rules[axis] = []
                setattr(target, level, rules)

        with transaction.atomic():
            editorial_line = getattr(instance, "editorialline", None)
            if editorial_line is not None:
                reset_rule_axes(editorial_line)
                editorial_line.save(update_fields=[*levels])

            blocks = list(
                GridBlock.objects
                .filter(grid_layout__tv_channel=instance)
            )
            for block in blocks:
                reset_rule_axes(block)
            if blocks:
                GridBlock.objects.bulk_update(blocks, fields=levels)

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
