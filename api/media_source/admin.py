from django.contrib import admin
from media_source.models import MediaContainer, MediaCollection, MediaSource, MediaItem

for element in [MediaSource, MediaCollection, MediaContainer, MediaItem]:
    admin.site.register(element)
