from project_ops.views.user_socket_views import UserSocketViewSet

from django.urls import path, include

from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register('user-socket', UserSocketViewSet, basename='user-socket')


# registration

urlpatterns = [
    path('', include(router.urls))
]