from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from tv_channel.models import GridBlock
from tv_channel.serializers.grid_block_serializers import GridBlockSerializer
from tv_channel.services.grid_block_service import GridBlockService


class GridBlockViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    serializer_class = GridBlockSerializer
    permission_classes = []

    def get_queryset(self):
        queryset = GridBlock.objects.all()
        return queryset

    def get_serializer_class(self):
        return super().get_serializer_class()

    @action(detail=True, url_path="available-media-count", methods=('get',))
    def available_media_count(self, request, pk):
        instance = self.get_object()
        service = GridBlockService(grid_block=instance)
        result = service.get_available_media_count()
        return Response(data={"count": result}, status=status.HTTP_200_OK)
