from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from grid_schedule.constants import ScheduledContainerStatus


class TvPlayout(models.Model):
    tv_channel = models.ForeignKey("tv_channel.TvChannel", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    grid = models.ForeignKey("tv_channel.GridLayout", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tv_channel"],
                condition=Q(is_active=True),
                name="unique_active_playout_per_channel",
            ),
        ]

    def __str__(self):
        return f"{self.pk} {self.tv_channel.name} Active: {self.is_active}"


class BlockContainerSelection(models.Model):
    order = models.PositiveIntegerField(default=0)  # horizontal, ordre parmi shows sélectionnés pour le block
    planned_item_count = models.PositiveIntegerField(default=1)  # nb d'épisode a diffuser
    status = models.IntegerField(choices=ScheduledContainerStatus, default=ScheduledContainerStatus.PENDING)

    media_container = models.ForeignKey("media_source.MediaContainer", on_delete=models.CASCADE)
    block = models.ForeignKey('tv_channel.GridBlock', on_delete=models.CASCADE)
    tv_playout = models.ForeignKey("TvPlayout", on_delete=models.CASCADE)
    last_scheduled_item = models.ForeignKey(
        "media_source.MediaItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        unique_together = ("tv_playout", "block", "order")

    def clean(self):
        if self.block.grid_layout_id != self.tv_playout.grid_id:
            raise ValidationError("Selected block must belong to the playout grid.")


class ScheduleMediaItem(models.Model):
    added_to_playout = models.BooleanField(default=False)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    item = models.ForeignKey('media_source.MediaItem', on_delete=models.CASCADE)
    block_container_selection = models.ForeignKey('BlockContainerSelection', on_delete=models.CASCADE)
    post_roll_filler_ends_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.block_container_selection.tv_playout.tv_channel.name} / {self.block_container_selection.block.starts_at} - {self.block_container_selection.media_container.title}"
