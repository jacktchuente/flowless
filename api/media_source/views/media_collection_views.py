from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from media_source.models import MediaCollection
from media_source.serializers.media_collection_serializers import (
    MediaCollectionSerializer,
    MediaCollectionUpdateSerializer,
)
from media_source.tasks import analyze_media_collection_data


class MediaCollectionViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = MediaCollectionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = MediaCollection.objects.select_related("media_source").all()
        media_source_id = self.request.query_params.get("media_source")
        if media_source_id:
            queryset = queryset.filter(media_source_id=media_source_id)
        return queryset.order_by("media_source_id", "name")

    def get_serializer_class(self):
        if self.action in ("partial_update", "update"):
            return MediaCollectionUpdateSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=("post",), url_name="analyze", url_path="analyze")
    def analyze(self, request, pk):
        instance = self.get_object()
        if not instance.is_active:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"detail": "La collection doit etre active avant analyse."},
            )
        analyze_media_collection_data.delay(instance.id)
        return Response(status=status.HTTP_200_OK)
