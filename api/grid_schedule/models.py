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


class FlexiblePlayoutSelection(models.Model):
    order = models.PositiveIntegerField(default=0)
    path_position = models.PositiveIntegerField()
    planned_item_count = models.PositiveIntegerField(default=1)
    status = models.IntegerField(choices=ScheduledContainerStatus, default=ScheduledContainerStatus.PENDING)

    tv_playout = models.ForeignKey(
        "TvPlayout",
        on_delete=models.CASCADE,
        related_name="flexible_selections",
    )
    segment = models.ForeignKey(
        "editorial_planning.EditorialSegment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="flexible_playout_selections",
    )
    media_container = models.ForeignKey("media_source.MediaContainer", on_delete=models.CASCADE)
    last_scheduled_item = models.ForeignKey(
        "media_source.MediaItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tv_playout", "order"],
                name="unique_flexible_selection_order_per_playout",
            ),
        ]
        indexes = [
            models.Index(fields=["tv_playout", "status"]),
            models.Index(fields=["segment", "status"]),
        ]

    def __str__(self):
        return f"{self.tv_playout.tv_channel.name} / flexible #{self.order} - {self.media_container.title}"


class ScheduleMediaItem(models.Model):
    added_to_playout = models.BooleanField(default=False)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    item = models.ForeignKey('media_source.MediaItem', on_delete=models.CASCADE)
    block_container_selection = models.ForeignKey(
        "BlockContainerSelection",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    flexible_selection = models.ForeignKey(
        "FlexiblePlayoutSelection",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    post_roll_filler_ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(block_container_selection__isnull=False, flexible_selection__isnull=True)
                    | Q(block_container_selection__isnull=True, flexible_selection__isnull=False)
                ),
                name="schedule_item_has_exactly_one_selection",
            ),
        ]

    def clean(self):
        has_fixed_selection = self.block_container_selection_id is not None
        has_flexible_selection = self.flexible_selection_id is not None
        if has_fixed_selection == has_flexible_selection:
            raise ValidationError("ScheduleMediaItem must have exactly one selection.")

    def __str__(self):
        if self.block_container_selection_id:
            return (
                f"{self.block_container_selection.tv_playout.tv_channel.name} / "
                f"{self.block_container_selection.block.starts_at} - "
                f"{self.block_container_selection.media_container.title}"
            )
        return (
            f"{self.flexible_selection.tv_playout.tv_channel.name} / flexible - "
            f"{self.flexible_selection.media_container.title}"
        )
