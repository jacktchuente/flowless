from media_source.views.media_container_views import MediaContainerViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from media_source.views.media_collection_views import MediaCollectionViewSet
from media_source.views.media_source_views import MediaSourceViewSet

router = DefaultRouter()

router.register('media-source', MediaSourceViewSet, basename='media-source')
router.register('media-collection', MediaCollectionViewSet, basename='media-collection')
router.register('media-container', MediaContainerViewSet, basename='media-container')
# registration

urlpatterns = [
    path('', include(router.urls))
]
