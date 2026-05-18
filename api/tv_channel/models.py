from datetime import time

from django.db import models
from django.utils.timezone import now

from project_ops.constants import AnalyzeStatus


class Catalog(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    analyze_status = models.IntegerField(choices=AnalyzeStatus, default=AnalyzeStatus.IDLE)
    number_of_channels = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name


class TvChannel(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    specification = models.TextField(null=True, blank=True,
                                     help_text="Technical description of the channel. More detailled")

    logo = models.FileField(upload_to="data/logos/", null=True, blank=True)
    external_playout_id = models.CharField(max_length=255, null=True, blank=True)
    catalog = models.ForeignKey("Catalog", on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=True)
    analyze_status = models.CharField(max_length=32, choices=AnalyzeStatus, default=AnalyzeStatus.IDLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class EditorialLine(models.Model):
    tv_channel = models.OneToOneField("TvChannel", on_delete=models.CASCADE)

    allowed_categories = models.JSONField(default=list, blank=True)
    forbidden_categories = models.JSONField(default=list, blank=True)
    preferred_categories = models.JSONField(default=list, blank=True)

    allowed_natures = models.JSONField(default=list, blank=True)
    forbidden_natures = models.JSONField(default=list, blank=True)
    preferred_natures = models.JSONField(default=list, blank=True)

    allowed_container_kinds = models.JSONField(default=list, blank=True)
    forbidden_container_kinds = models.JSONField(default=list, blank=True)
    preferred_container_kinds = models.JSONField(default=list, blank=True)

    # diffusion
    start_at = models.TimeField(default=time(6, 0))
    end_at = models.TimeField(default=time(22, 0))
    allow_filler = models.BooleanField(default=True)


class GridLayout(models.Model):
    tv_channel = models.ForeignKey("TvChannel", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=now)
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tv_channel"],
                condition=models.Q(is_active=True),
                name="unique_active_grid_layout_per_channel",
            )
        ]


class GridBlock(models.Model):
    grid_layout = models.ForeignKey("GridLayout", on_delete=models.CASCADE)

    starts_at = models.TimeField()
    ends_at = models.TimeField()

    priority = models.PositiveIntegerField(default=50)  # which block chose first

    # mode de remplissage
    min_items = models.PositiveIntegerField(default=1)
    max_items = models.PositiveIntegerField(default=1)
    min_duration_seconds_per_item = models.PositiveIntegerField(null=True, blank=True)
    max_duration_seconds_per_item = models.PositiveIntegerField(null=True, blank=True)

    # block editorial rules

    allowed_categories = models.JSONField(default=list)
    forbidden_categories = models.JSONField(default=list)
    preferred_categories = models.JSONField(default=list)

    allowed_natures = models.JSONField(default=list)
    forbidden_natures = models.JSONField(default=list)
    preferred_natures = models.JSONField(default=list)

    allowed_container_kinds = models.JSONField(default=list)
    forbidden_container_kinds = models.JSONField(default=list)
    preferred_container_kinds = models.JSONField(default=list)

    post_filler_policy = models.ForeignKey("FillerPolicy", on_delete=models.SET_NULL, blank=True, null=True)


class FillerPolicy(models.Model):
    """
    The slot for fillers. Handle based on duration only. For now. 
    Eventually, count &
    """
    name = models.CharField(max_length=80)
    duration_seconds = models.PositiveIntegerField(default=180)

    def __str__(self):
        return self.name
