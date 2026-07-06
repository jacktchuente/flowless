from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from tv_channel.models import Catalog
from tv_channel.serializers.catalog_serializers import (
    CatalogCreateSerializer,
    CatalogSerializer,
    CatalogUpdateSerializer,
)
from tv_channel.tasks import generate_catalog_channels
from editorial_planning.serializers.planning_serializers import EditorialPlanningGenerationRequestSerializer
from editorial_planning.tasks import generate_editorial_planning as generate_editorial_planning_task


class CatalogViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = CatalogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Catalog.objects.all().order_by("name")

    def get_serializer_class(self):
        if self.action == "create":
            return CatalogCreateSerializer
        if self.action in ("partial_update", "update"):
            return CatalogUpdateSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=("post",), url_name="generate-channels", url_path="generate-channels")
    def generate_channels(self, request, pk=None):
        instance = self.get_object()
        reboot = str(request.data.get("reboot", "")).lower() in {"1", "true", "yes", "on"}
        generate_catalog_channels.delay(instance.id, reboot=reboot)
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=("post",), url_name="generate-editorial-planning", url_path="generate-editorial-planning")
    def generate_editorial_planning(self, request, pk=None):
        instance = self.get_object()
        serializer = EditorialPlanningGenerationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        generate_editorial_planning_task.delay(
            instance.id,
            media_collection_ids=serializer.validated_data["media_collection_ids"],
            max_channel_candidates=serializer.validated_data.get("max_channel_candidates"),
            target_channel_count=serializer.validated_data.get("target_channel_count"),
            allow_multi_segment=serializer.validated_data.get("allow_multi_segment", True),
            allow_segment_sharing=serializer.validated_data.get("allow_segment_sharing", False),
            refine_membership_threshold=serializer.validated_data.get("refine_membership_threshold"),
        )
        return Response(status=status.HTTP_202_ACCEPTED)
    
    #
    # @action(detail=True, methods=("post",), url_name="generate-blueprints", url_path="generate-blueprints")
    # def generate_blueprints(self, request, pk=None):
    #     instance = self.get_object()
    #     reboot = str(request.data.get("reboot", "")).lower() in {"1", "true", "yes", "on"}
    #     grid_mode = request.data.get("grid_mode", "full")
    #     generate_tv_channel_blueprint_for_catalog.delay(instance.id, reboot=reboot, grid_mode=grid_mode)
    #     return Response(status=status.HTTP_202_ACCEPTED)
    #
    # @action(detail=True, methods=("post",), url_name="generate-playouts", url_path="generate-playouts")
    # def generate_playouts(self, request, pk=None):
    #     instance = self.get_object()
    #     days = int(request.data.get("days", 1))
    #     reset = str(request.data.get("reset", "")).lower() in {"1", "true", "yes", "on"}
    #     force_bypass_mandatory = str(request.data.get("force_bypass_mandatory", "")).lower() in {"1", "true", "yes", "on"}
    #     generate_tv_channel_playout_for_catalog.delay(
    #         instance.id,
    #         days=days,
    #         reset=reset,
    #         force_bypass_mandatory=force_bypass_mandatory,
    #     )
    #     return Response(status=status.HTTP_202_ACCEPTED)
    #
    # @action(detail=True, methods=("post",), url_name="push-etv", url_path="push-etv")
    # def push_etv(self, request, pk=None):
    #     instance = self.get_object()
    #     push_tv_channel_to_etv_for_catalog.delay(instance.id)
    #     return Response(status=status.HTTP_202_ACCEPTED)
    #
    # @action(detail=True, methods=("post",), url_name="mark-ready", url_path="mark-ready")
    # def mark_ready(self, request, pk=None):
    #     instance = self.get_object()
    #     channel_ids = list(
    #         TvChannel.objects
    #         .filter(catalog_id=instance.id)
    #         .values_list("id", flat=True)
    #     )
    #     TvChannel.objects.filter(id__in=channel_ids).update(status=TvChannelStatus.READY)
    #     for channel_id in channel_ids:
    #         broadcast_crud_event(object_type="TvChannel", object_id=channel_id, action="update")
    #     return Response(status=status.HTTP_200_OK)
    #
    # @action(detail=True, methods=("get",), url_name="download-generation-prompt", url_path="download-generation-prompt")
    # def download_generation_prompt(self, request, pk=None):
    #     instance = self.get_object()
    #     prompt = CatalogGeneratorService(catalog=instance, reboot=True).generate_prompt()
    #     response = HttpResponse(prompt, content_type="text/plain; charset=utf-8")
    #     response["Content-Disposition"] = f'attachment; filename="catalog-generation-prompt-{instance.id}.txt"'
    #     return response
    #
    # @action(
    #     detail=True,
    #     methods=("post",),
    #     url_name="upload-generation-response",
    #     url_path="upload-generation-response",
    #     parser_classes=[MultiPartParser],
    # )
    # def upload_generation_response(self, request, pk=None):
    #     instance = self.get_object()
    #     response_file = request.FILES.get("file")
    #     if response_file is None:
    #         return Response({"detail": "Le fichier est requis."}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     storage_name = default_storage.save(
    #         f"tv_channel/catalog_generation_uploads/{timezone.now().strftime('%Y%m%d%H%M%S')}_{response_file.name}",
    #         response_file,
    #     )
    #     process_catalog_generation_response_upload.delay(instance.id, default_storage.path(storage_name))
    #     return Response(status=status.HTTP_202_ACCEPTED)
    #
    # @action(
    #     detail=True,
    #     methods=("get",),
    #     url_name="download-channel-blueprint-prompts",
    #     url_path="download-channel-blueprint-prompts",
    # )
    # def download_channel_blueprint_prompts(self, request, pk=None):
    #     instance = self.get_object()
    #     channel_ids = request.query_params.getlist("channel")
    #     queryset = TvChannel.objects.filter(catalog_id=instance.id).order_by("name")
    #     if channel_ids:
    #         queryset = queryset.filter(id__in=channel_ids)
    #
    #     buffer = BytesIO()
    #     with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    #         for channel in queryset:
    #             prompt_bundle = ChannelBluePrintService(tv_channel=channel, reboot=True).generate_prompt_bundle(persist=True)
    #             archive.writestr(f"{channel.pk}.txt", prompt_bundle)
    #
    #     response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    #     response["Content-Disposition"] = f'attachment; filename="channel-blueprint-prompts-{instance.id}.zip"'
    #     return response
    #
    # @action(
    #     detail=True,
    #     methods=("post",),
    #     url_name="upload-channel-blueprint-responses",
    #     url_path="upload-channel-blueprint-responses",
    #     parser_classes=[MultiPartParser],
    # )
    # def upload_channel_blueprint_responses(self, request, pk=None):
    #     instance = self.get_object()
    #     archive_file = request.FILES.get("file")
    #     if archive_file is None:
    #         return Response({"detail": "Le fichier archive est requis."}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     storage_name = default_storage.save(
    #         f"tv_channel/channel_blueprint_uploads/{timezone.now().strftime('%Y%m%d%H%M%S')}_{archive_file.name}",
    #         archive_file,
    #     )
    #     process_channel_blueprint_archive_upload.delay(instance.id, default_storage.path(storage_name))
    #     return Response(status=status.HTTP_202_ACCEPTED)
    #
    # @action(
    #     detail=True,
    #     methods=("get",),
    #     url_name="download-channel-logo-prompts",
    #     url_path="download-channel-logo-prompts",
    # )
    # def download_channel_logo_prompts(self, request, pk=None):
    #     instance = self.get_object()
    #     channel_ids = request.query_params.getlist("channel")
    #     queryset = TvChannel.objects.filter(catalog_id=instance.id).order_by("name")
    #     if channel_ids:
    #         queryset = queryset.filter(id__in=channel_ids)
    #
    #     buffer = BytesIO()
    #     with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    #         for channel in queryset:
    #             prompt = LogoPromptService(tv_channel=channel).generate_prompt()
    #             archive.writestr(f"{channel.pk}.txt", prompt)
    #
    #     response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    #     response["Content-Disposition"] = f'attachment; filename="channel-logo-prompts-{instance.id}.zip"'
    #     return response
    #
    # @action(
    #     detail=True,
    #     methods=("post",),
    #     url_name="upload-channel-logo-responses",
    #     url_path="upload-channel-logo-responses",
    #     parser_classes=[MultiPartParser],
    # )
    # def upload_channel_logo_responses(self, request, pk=None):
    #     instance = self.get_object()
    #     archive_file = request.FILES.get("file")
    #     if archive_file is None:
    #         return Response({"detail": "Le fichier archive est requis."}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     storage_name = default_storage.save(
    #         f"tv_channel/channel_logo_uploads/{timezone.now().strftime('%Y%m%d%H%M%S')}_{archive_file.name}",
    #         archive_file,
    #     )
    #     process_channel_logo_archive_upload.delay(instance.id, default_storage.path(storage_name))
    #     return Response(status=status.HTTP_202_ACCEPTED)
