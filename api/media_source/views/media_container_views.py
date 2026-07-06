from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from media_source.models import MediaContainer
from media_source.serializers.media_container_serializers import MediaContainerSerializer, \
    MediaContainerDetailSerializer
from media_source.tasks import analyze_all_media_container_data, analyze_media_container_data
from utils.pagination import StandardResultsSetPagination
from rest_framework.decorators import action


class MediaContainerViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    serializer_class = MediaContainerSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = MediaContainer.objects.filter(media_collection__is_active=True)
        title = self.request.query_params.get("title")
        status_value = self.request.query_params.get("status")
        category = self.request.query_params.get("category")
        nature = self.request.query_params.get("nature")
        container_kind = self.request.query_params.get("container_kind")
        is_anime = self.request.query_params.get("is_anime")
        media_collection_id = self.request.query_params.get("media_collection")

        if media_collection_id:
            queryset = queryset.filter(media_collection_id=media_collection_id)
        if title:
            queryset = queryset.filter(title__icontains=title)
        if status_value not in (None, ""):
            queryset = queryset.filter(analyze_status=status_value)
        if category:
            queryset = queryset.filter(categories__contains=[category])
        if nature not in (None, ""):
            queryset = queryset.filter(media_collection__nature=nature)
        if container_kind not in (None, ""):
            queryset = queryset.filter(media_collection__container_kind=container_kind)
        if is_anime not in (None, ""):
            queryset = queryset.filter(media_collection__is_anime=str(is_anime).lower() in {"1", "true", "yes"})

        return queryset.order_by("pk")

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MediaContainerDetailSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=('post',), url_path="analyse", url_name="analyse")
    def analyse(self, request, pk):
        instance = self.get_object()
        analyze_media_container_data.delay(instance.pk)
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=('post',), url_path="analyse-all", url_name="analyse-all")
    def analyse_all(self, request):
        analyze_all_media_container_data.delay()
        return Response(status=status.HTTP_202_ACCEPTED)
