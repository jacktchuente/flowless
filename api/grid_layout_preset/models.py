from django.db import models


class GridLayoutPreset(models.Model):
    name = models.CharField(unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name


class GridBlockPreset(models.Model):
    grid_layout = models.ForeignKey("GridLayoutPreset", on_delete=models.CASCADE)

    starts_at = models.TimeField()
    ends_at = models.TimeField()

    priority = models.PositiveIntegerField(default=50)

    min_items = models.PositiveIntegerField(default=1)
    max_items = models.PositiveIntegerField(default=1)
    min_duration_seconds_per_item = models.PositiveIntegerField(null=True, blank=True)
    max_duration_seconds_per_item = models.PositiveIntegerField(null=True, blank=True)

    # dicts keyed by rule axis: categories / natures / container_kinds
    allowed = models.JSONField(default=dict, blank=True)
    preferred = models.JSONField(default=dict, blank=True)
    forbidden = models.JSONField(default=dict, blank=True)

    post_filler_policy = models.ForeignKey("FillerPolicyPreset", on_delete=models.SET_NULL, blank=True, null=True)

    required_fields = models.JSONField(default=list)


class FillerPolicyPreset(models.Model):
    name = models.CharField(max_length=80, null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=180)
