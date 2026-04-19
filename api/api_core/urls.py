from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('djx_account.urls')),
    path('api/', include('djx_websocket.urls')),

]
