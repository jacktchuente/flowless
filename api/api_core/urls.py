from django.contrib import admin
from django.conf import settings
from django.urls import path, include, re_path

from project_ops.views.media_views import media_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('djx_account.urls')),
    # path('api/', include('djx_websocket.urls')),
    path('api/', include('project_ops.urls')),
    path('api/', include('media_source.urls')),
    path('api/', include('tv_channel.urls')),
    path('api/', include('grid_schedule.urls')),
    path('api/', include('editorial_planning.urls')),
    path('api/', include('dashboard.urls')),

]

# Les medias sont servis par Django (plus de nginx devant uvicorn).
_media_prefix = settings.MEDIA_URL.lstrip("/")
urlpatterns += [
    re_path(rf"^{_media_prefix}(?P<path>.*)$", media_serve),
]
