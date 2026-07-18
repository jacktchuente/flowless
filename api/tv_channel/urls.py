from tv_channel.views.channel_image_views import ChannelImageSuggestionRunViewSet
from tv_channel.views.grid_block_views import GridBlockViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from tv_channel.views.catalog_views import CatalogViewSet
from tv_channel.views.tv_channel_views import TvChannelViewSet

router = DefaultRouter()
router.register('catalog', CatalogViewSet, basename='catalog')
router.register('tv-channel', TvChannelViewSet, basename='tv-channel')

router.register('grid-block', GridBlockViewSet, basename='grid-block')
router.register('channel-image-run', ChannelImageSuggestionRunViewSet, basename='channel-image-run')
# registration

urlpatterns = [
    path('', include(router.urls))
]
