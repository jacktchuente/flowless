from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from editorial_planning.models import EditorialChannelCandidate, EditorialFlowRun
from editorial_planning.serializers.planning_serializers import (
    EditorialChannelCandidateSerializer,
    EditorialFlexibleChannelCreateSerializer,
    EditorialFlowRunSerializer,
)
from editorial_planning.services.channel_creation_service import EditorialFlexibleChannelCreationService
from tv_channel.serializers.tv_channel_serializers import TvChannelSerializer


class EditorialFlowRunViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = EditorialFlowRunSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = (
            EditorialFlowRun.objects.select_related("catalog")
            .prefetch_related(
                "channel_candidates",
                "channel_candidates__channel_segments",
                "channel_candidates__channel_segments__segment",
                "channel_candidates__segment_path",
                "channel_candidates__segment_path__elements",
                "channel_candidates__segment_path__elements__segment",
            )
            .all()
        )
        catalog_id = self.request.query_params.get("catalog")
        if catalog_id:
            queryset = queryset.filter(catalog_id=catalog_id)
        return queryset.order_by("-created_at", "-id")


class EditorialChannelCandidateViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = EditorialChannelCandidateSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = (
            EditorialChannelCandidate.objects.select_related(
                "run",
                "run__catalog",
                "tv_channel",
                "segment_path",
            )
            .prefetch_related(
                "channel_segments",
                "channel_segments__segment",
                "segment_path__elements",
                "segment_path__elements__segment",
            )
            .all()
        )
        run_id = self.request.query_params.get("run")
        if run_id:
            queryset = queryset.filter(run_id=run_id)
        catalog_id = self.request.query_params.get("catalog")
        if catalog_id:
            queryset = queryset.filter(run__catalog_id=catalog_id)
        return queryset.order_by("-viability_score", "name", "id")

    @action(detail=True, methods=("post",), url_name="create-flexible-channel", url_path="create-flexible-channel")
    def create_flexible_channel(self, request, pk=None):
        candidate = self.get_object()
        serializer = EditorialFlexibleChannelCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tv_channel = EditorialFlexibleChannelCreationService(channel_candidate=candidate).create_channel(
            name=serializer.validated_data.get("name") or None,
        )
        return Response(TvChannelSerializer(tv_channel, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)
