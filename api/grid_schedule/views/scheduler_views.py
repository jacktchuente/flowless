import logging
from django.core.exceptions import ValidationError
from tv_channel.models import TvChannel

from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from grid_schedule.services.etv_scheduler_service import ETVSchedulerService

logger = logging.getLogger(__name__)


class SchedulerViewSet(GenericViewSet):
    permission_classes = []

    @action(detail=False, methods=("post",), url_path="build")
    def build(self, request):
        build_id = request.data.get("build_id")
        if build_id is None:
            return Response({"detail": "build_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        mode = request.data.get("mode")
        channel_key = request.data.get("channel_name")
        if not channel_key:
            return Response({"detail": "channel_key is required."}, status=status.HTTP_400_BAD_REQUEST)
        profile = request.data.get("profile", "drama")
        try:
            result = ETVSchedulerService(
                channel_key=channel_key,
                build_id=build_id,
                mode=mode,
                profile=profile,
            ).run()
        except TvChannel.DoesNotExist:
            return Response({"detail": "Unknown channel_key."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "status": "ok",
                "build_id": build_id,
                "mode": mode,
                "profile": profile,
                **result.to_dict(),
            }
        )
