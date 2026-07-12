from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from tv_channel.models import GridBlock
from tv_channel.serializers.grid_block_serializers import (
    GridBlockSerializer,
    GridBlockWriteSerializer,
)
from tv_channel.services.grid_block_service import GridBlockService
from tv_channel.services.grid_editing import (
    GridNotEditableError,
    ensure_block_is_editable,
    get_editable_grid_layout,
)


class GridBlockViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = GridBlockSerializer
    permission_classes = []

    def get_queryset(self):
        queryset = GridBlock.objects.all()
        return queryset

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return GridBlockWriteSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        layout = serializer.validated_data["grid_layout"]
        try:
            active = get_editable_grid_layout(layout.tv_channel)
        except GridNotEditableError as exc:
            raise ValidationError({"grid_layout": str(exc)})
        if active.pk != layout.pk:
            raise ValidationError(
                {"grid_layout": "Only the active grid can be edited."}
            )
        serializer.save()

    def perform_update(self, serializer):
        self._ensure_editable(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_editable(instance)
        instance.delete()

    @staticmethod
    def _ensure_editable(block):
        try:
            ensure_block_is_editable(block)
        except GridNotEditableError as exc:
            raise ValidationError({"detail": str(exc)})

    @action(detail=True, url_path="available-media-count", methods=("get", "post"))
    def available_media_count(self, request, pk):
        instance = self.get_object()
        preview = instance
        if request.method == "POST":
            serializer = GridBlockWriteSerializer(
                instance=instance,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            preview = copy(instance)
            for field, value in serializer.validated_data.items():
                setattr(preview, field, value)

        service = GridBlockService(grid_block=preview)
        result = service.get_available_media_count()
        return Response(data={"count": result}, status=status.HTTP_200_OK)


from copy import copy
