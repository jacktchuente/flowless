from djx_websocket.models import UserSocket
from djx_websocket.serializers.user_socket_serializers import UserSocketSerializer
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class UserSocketViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = UserSocketSerializer
    permission_classes = []
    queryset = UserSocket.objects.none()

    def retrieve(self, request, *args, **kwargs):
        return Response({})
