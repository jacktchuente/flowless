from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from media_source.models import MediaSource
from media_source.serializers.media_source_serializers import MediaSourceCreateSerializer, \
    MediaSourceSerializer
from media_source.services.media_source_service import MediaSourceService
from media_source.tasks import analyze_media_source_data


class MediaSourceViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet
):
    serializer_class = MediaSourceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = MediaSource.objects.all()
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return MediaSourceCreateSerializer
        if self.action == 'partial_update' or self.action == 'update':
            return MediaSourceCreateSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=('post',), url_name='analyze', url_path='analyze')
    def analyze(self, request, pk):
        instance = self.get_object()
        analyze_media_source_data.delay(instance.id)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=('post',), url_name='verify', url_path='verify')
    def verify(self, request, pk):
        instance = self.get_object()
        service = MediaSourceService(instance)
        is_ok = service.check_credentials()
        return Response(status=status.HTTP_200_OK, data={"is_ok": is_ok})

    @action(detail=False, methods=('post',), url_name='verify-credentials', url_path='verify')
    def verify_credentials(self, request):
        serializer = MediaSourceCreateSerializer(data={
            "name": request.data.get("name", "tmp"),
            "credentials": request.data.get("credentials", {}),
            "source_type": request.data.get("source_type"),
        })
        serializer.is_valid(raise_exception=True)
        is_ok = MediaSourceService.validate_credentials(serializer.validated_data["credentials"])
        if not is_ok:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    "is_ok": False,
                    "credentials": ["Impossible de se connecter a Jellyfin avec ces credentials."],
                },
            )
        return Response(status=status.HTTP_200_OK, data={"is_ok": True})
