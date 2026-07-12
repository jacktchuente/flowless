from django.db import connections
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from project_ops.services.heartbeat import scheduler_is_alive


class HealthView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        database_ok = True
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            database_ok = False

        scheduler_ok, heartbeat_age = scheduler_is_alive()

        healthy = database_ok and scheduler_ok
        return Response(
            {
                "status": "ok" if healthy else "degraded",
                "database": database_ok,
                "scheduler": scheduler_ok,
                "scheduler_heartbeat_age_seconds": heartbeat_age,
            },
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
