from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from editorial_planning.models import (
    EditorialChannelCandidate,
    EditorialFlowRun,
    EditorialSegment,
    EditorialSegmentMembership,
)
from editorial_planning.serializers.planning_serializers import (
    EditorialChannelCandidateSerializer,
    EditorialFlexibleChannelCreateSerializer,
    EditorialFlowRunSerializer,
    EditorialSegmentMembershipSerializer,
    EditorialSegmentMembershipStatusSerializer,
    EditorialSegmentSerializer,
)
from editorial_planning.services.channel_creation_service import EditorialFlexibleChannelCreationService
from editorial_planning.tasks import match_new_media_to_editorial_run
from tv_channel.serializers.tv_channel_serializers import TvChannelSerializer


class EditorialFlowRunViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = EditorialFlowRunSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=("post",), url_name="match-new-media", url_path="match-new-media")
    def match_new_media(self, request, pk=None):
        run = self.get_object()
        match_new_media_to_editorial_run.delay(run.id)
        return Response(status=status.HTTP_202_ACCEPTED)

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


class EditorialSegmentViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = EditorialSegmentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = EditorialSegment.objects.select_related("run").all()
        run_id = self.request.query_params.get("run")
        if run_id:
            queryset = queryset.filter(run_id=run_id)
        catalog_id = self.request.query_params.get("catalog")
        if catalog_id:
            queryset = queryset.filter(run__catalog_id=catalog_id)
        if self.request.query_params.get("active_run") in {"1", "true"}:
            queryset = queryset.filter(run__is_active=True)
        return queryset.order_by("-programmable_score", "name", "id")


class EditorialSegmentMembershipViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = EditorialSegmentMembershipSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = EditorialSegmentMembership.objects.select_related(
            "segment",
            "media_container",
        ).all()
        segment_id = self.request.query_params.get("segment")
        if segment_id:
            queryset = queryset.filter(segment_id=segment_id)
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset.order_by("-score", "media_container_id")

    @action(detail=True, methods=("post",), url_name="set-status", url_path="set-status")
    def set_status(self, request, pk=None):
        membership = self.get_object()
        serializer = EditorialSegmentMembershipStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership.status = serializer.validated_data["status"]
        membership.decision_reason = "Manual review"
        membership.save(update_fields=["status", "decision_reason", "updated_at"])
        return Response(
            EditorialSegmentMembershipSerializer(membership, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )


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
