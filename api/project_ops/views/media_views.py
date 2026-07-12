from django.conf import settings
from django.views.static import serve


def media_serve(request, path):
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response
