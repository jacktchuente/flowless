from django.db import models

from media_source.constants import MediaSourceType, MediaNature, \
    MediaContainerKind, MediaProgrammingRole
from project_ops.constants import AnalyzeStatus


class MediaSource(models.Model):
    name = models.CharField(max_length=20)
    credentials = models.JSONField(default=dict)
    source_type = models.IntegerField(default=MediaSourceType.jellyfin)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    analyze_status = models.IntegerField(choices=AnalyzeStatus, default=AnalyzeStatus.IDLE)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class MediaCollection(models.Model):
    name = models.CharField(max_length=20)
    external_id = models.CharField(max_length=255)
    media_source = models.ForeignKey("MediaSource", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    analyze_status = models.IntegerField(choices=AnalyzeStatus, default=AnalyzeStatus.IDLE)
    programming_role = models.IntegerField(choices=MediaProgrammingRole, null=True, blank=True)
    nature = models.IntegerField(choices=MediaNature, null=True, blank=True)
    hash_data = models.TextField()
    container_kind = models.IntegerField(choices=MediaContainerKind, null=True, blank=True)
    is_anime = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.media_source.name} - {self.name}"

    class Meta:
        unique_together = ('external_id', 'media_source')


class MediaContainer(models.Model):
    original_data_hash = models.TextField()

    external_id = models.CharField(max_length=255)
    provider_ids = models.JSONField(default=dict, blank=True)

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    media_source = models.ForeignKey("MediaSource", on_delete=models.CASCADE)
    media_collection = models.ForeignKey("MediaCollection", on_delete=models.CASCADE)

    analyzed_at = models.DateTimeField(null=True, blank=True)
    analyze_status = models.IntegerField(choices=AnalyzeStatus, default=0)

    categories = models.JSONField(default=list)

    # données agrégées ou éditoriales
    item_count = models.PositiveIntegerField(null=True, blank=True)

    duration_min_seconds = models.PositiveIntegerField(null=True, blank=True)
    duration_max_seconds = models.PositiveIntegerField(null=True, blank=True)
    total_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    min_video_width = models.PositiveIntegerField(null=True, blank=True)
    min_video_height = models.PositiveIntegerField(null=True, blank=True)

    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    release_date_start = models.DateField(null=True, blank=True)
    release_date_end = models.DateField(null=True, blank=True)
    release_year_min = models.PositiveSmallIntegerField(null=True, blank=True)
    release_year_max = models.PositiveSmallIntegerField(null=True, blank=True)
    countries = models.JSONField(default=list)
    audio_languages = models.JSONField(default=list)
    subtitle_languages = models.JSONField(default=list)
    audio_languages_any = models.JSONField(default=list)
    subtitle_languages_any = models.JSONField(default=list)
    community_rating_score = models.FloatField(null=True, blank=True)
    critic_rating_score = models.FloatField(null=True, blank=True)
    overall_rating_score = models.FloatField(null=True, blank=True)

    people = models.JSONField(default=list)
    directors = models.JSONField(default=list)
    writers = models.JSONField(default=list)
    creators = models.JSONField(default=list)
    actors = models.JSONField(default=list)
    studios = models.JSONField(default=list)

    tags = models.JSONField(default=list)
    genres = models.JSONField(default=list)
    raw_data = models.JSONField(default=dict)
    is_missing = models.BooleanField(default=False)

    class Meta:
        unique_together = ("external_id", "media_source")

    def __str__(self):
        return self.title


class MediaItem(models.Model):
    original_data_hash = models.TextField()

    container = models.ForeignKey(
        "MediaContainer",
        on_delete=models.CASCADE,
        related_name="items",
    )

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    item_kind = models.CharField(max_length=32, null=True, blank=True)

    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    # utile pour séries / ordre / redondance
    sequence_number = models.PositiveIntegerField(null=True, blank=True)
    season_number = models.PositiveIntegerField(null=True, blank=True)
    episode_number = models.PositiveIntegerField(null=True, blank=True)

    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    release_year = models.PositiveSmallIntegerField(null=True, blank=True)
    countries = models.JSONField(default=list)
    audio_languages = models.JSONField(default=list)
    subtitle_languages = models.JSONField(default=list)
    video_width = models.PositiveIntegerField(null=True, blank=True)
    video_height = models.PositiveIntegerField(null=True, blank=True)
    community_rating_score = models.FloatField(null=True, blank=True)
    critic_rating_score = models.FloatField(null=True, blank=True)
    overall_rating_score = models.FloatField(null=True, blank=True)

    tags = models.JSONField(default=list)
    genres = models.JSONField(default=list)

    people = models.JSONField(default=list)
    directors = models.JSONField(default=list)
    writers = models.JSONField(default=list)
    creators = models.JSONField(default=list)
    actors = models.JSONField(default=list)
    studios = models.JSONField(default=list)

    is_active = models.BooleanField(default=True)
    media_source = models.ForeignKey("MediaSource", on_delete=models.CASCADE)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    analyze_status = models.IntegerField(choices=AnalyzeStatus, default=AnalyzeStatus.IDLE)
    external_id = models.CharField(max_length=255)

    is_missing = models.BooleanField(default=False)

    raw_data = models.JSONField(default=dict)

    class Meta:
        unique_together = ("external_id", "media_source")

    def __str__(self):
        return f"{self.container.title} - {self.title}"
