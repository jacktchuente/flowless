from project_ops.views.health_views import HealthView
from project_ops.views.user_socket_views import UserSocketViewSet

from django.urls import path, include

from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register('user-socket', UserSocketViewSet, basename='user-socket')


# registration

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('', include(router.urls))
]