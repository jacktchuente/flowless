from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('djx_account.urls')),
    # path('api/', include('djx_websocket.urls')),
    path('api/', include('project_ops.urls')),
    path('api/', include('media_source.urls')),
    path('api/', include('tv_channel.urls')),
    path('api/', include('grid_schedule.urls')),

]

if settings.DEBUG:
    urlpatterns += static(
        getattr(settings, "MEDIA_URL", "/medias/"),
        document_root=settings.MEDIA_ROOT,
    )
