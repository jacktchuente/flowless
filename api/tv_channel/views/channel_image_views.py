from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from tv_channel.models import ChannelImageSuggestionRun
from tv_channel.serializers.image_suggestion_serializers import (
    ChannelImageChooseSerializer,
    ChannelImageSuggestionRunCreateSerializer,
    ChannelImageSuggestionRunSerializer,
)
from tv_channel.serializers.tv_channel_serializers import TvChannelSerializer
from tv_channel.services.image_suggestion.apply_service import ChannelImageApplyService
from tv_channel.tasks import generate_channel_image_suggestions


class ChannelImageSuggestionRunViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = ChannelImageSuggestionRunSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = (
            ChannelImageSuggestionRun.objects
            .select_related("tv_channel")
            .prefetch_related("suggestions")
        )
        channel_id = self.request.query_params.get("tv_channel")
        if channel_id:
            queryset = queryset.filter(tv_channel_id=channel_id)
        return queryset.order_by("-created_at", "-id")

    def create(self, request):
        serializer = ChannelImageSuggestionRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        generate_channel_image_suggestions.delay(
            data["tv_channel"].id,
            kind=data["kind"],
            query=data.get("query") or None,
            entity_type=data.get("entity_type") or None,
        )
        return Response(status=status.HTTP_202_ACCEPTED)

    def perform_destroy(self, instance):
        for suggestion in instance.suggestions.all():
            if suggestion.thumbnail:
                suggestion.thumbnail.delete(save=False)
        instance.delete()

    @action(detail=True, methods=("post",), url_path="choose")
    def choose(self, request, pk=None):
        run = self.get_object()
        serializer = ChannelImageChooseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion = run.suggestions.filter(pk=serializer.validated_data["suggestion_id"]).first()
        if suggestion is None:
            return Response(
                {"suggestion_id": "Suggestion does not belong to this run."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tv_channel = ChannelImageApplyService(suggestion).apply()
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(TvChannelSerializer(tv_channel).data)
