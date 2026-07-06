from django.db import models

from project_ops.constants import AnalyzeStatus


class EditorialSegmentMembershipStatus(models.TextChoices):
    ACCEPTED = "accepted", "accepted"
    SECONDARY = "secondary", "secondary"
    AMBIGUOUS = "ambiguous", "ambiguous"
    REJECTED = "rejected", "rejected"
    PENDING = "pending", "pending"
    MANUAL_OVERRIDE = "manual_override", "manual_override"


class EditorialChannelCandidateStatus(models.TextChoices):
    VIABLE = "viable", "viable"
    WEAK = "weak", "weak"
    REJECTED = "rejected", "rejected"
    SELECTED = "selected", "selected"
    PUBLISHED = "published", "published"


class EditorialSegmentRole(models.TextChoices):
    ANCHOR = "anchor", "anchor"
    SUPPORT = "support", "support"
    SECONDARY = "secondary", "secondary"


class EditorialFlowRun(models.Model):
    catalog = models.ForeignKey(
        "tv_channel.Catalog",
        on_delete=models.CASCADE,
        related_name="editorial_flow_runs",
    )
    status = models.IntegerField(choices=AnalyzeStatus, default=AnalyzeStatus.IDLE)
    is_active = models.BooleanField(default=False)

    algorithm_version = models.CharField(max_length=32, default="1.0")
    config = models.JSONField(default=dict, blank=True)
    model_state = models.JSONField(default=dict, blank=True)
    diagnostics = models.JSONField(default=dict, blank=True)

    source_media_count = models.PositiveIntegerField(default=0)
    segment_count = models.PositiveIntegerField(default=0)
    channel_candidate_count = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("catalog", "is_active")),
        ]

    def __str__(self):
        return f"{self.catalog.name} / editorial flow #{self.id}"


class EditorialSegment(models.Model):
    run = models.ForeignKey(
        "editorial_planning.EditorialFlowRun",
        on_delete=models.CASCADE,
        related_name="segments",
    )
    segment_key = models.CharField(max_length=64)

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    profile = models.JSONField(default=dict, blank=True)
    reference_vector = models.JSONField(default=list, blank=True)
    reference_profile = models.JSONField(default=dict, blank=True)
    observed_profile = models.JSONField(default=dict, blank=True)

    programmable_score = models.FloatField(default=0.0)
    cohesion_score = models.FloatField(default=0.0)
    separation_score = models.FloatField(default=0.0)
    format_consistency_score = models.FloatField(default=0.0)
    volume_score = models.FloatField(default=0.0)
    labelability_score = models.FloatField(default=0.0)
    acceptance_threshold = models.FloatField(default=0.0)
    media_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-programmable_score", "name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("run", "segment_key"),
                name="unique_editorial_segment_key_per_run",
            ),
        ]
        indexes = [
            models.Index(fields=("run", "segment_key")),
        ]

    def __str__(self):
        return self.name


class EditorialSegmentMembership(models.Model):
    segment = models.ForeignKey(
        "editorial_planning.EditorialSegment",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    media_container = models.ForeignKey(
        "media_source.MediaContainer",
        on_delete=models.CASCADE,
        related_name="editorial_segment_memberships",
    )
    score = models.FloatField(default=0.0)
    is_primary = models.BooleanField(default=True)
    status = models.CharField(
        max_length=32,
        choices=EditorialSegmentMembershipStatus,
        default=EditorialSegmentMembershipStatus.ACCEPTED,
    )
    decision_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("segment", "-score", "media_container")
        constraints = [
            models.UniqueConstraint(
                fields=("segment", "media_container"),
                name="unique_editorial_segment_membership",
            ),
        ]
        indexes = [
            models.Index(fields=("media_container", "status")),
        ]

    def __str__(self):
        return f"{self.segment.name} / {self.media_container.title}"


class EditorialChannelCandidate(models.Model):
    run = models.ForeignKey(
        "editorial_planning.EditorialFlowRun",
        on_delete=models.CASCADE,
        related_name="channel_candidates",
    )
    channel_key = models.CharField(max_length=64)
    tv_channel = models.ForeignKey(
        "tv_channel.TvChannel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editorial_channel_candidates",
    )

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    viability_score = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=32,
        choices=EditorialChannelCandidateStatus,
        default=EditorialChannelCandidateStatus.VIABLE,
    )
    profile = models.JSONField(default=dict, blank=True)
    diagnostics = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-viability_score", "name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("run", "channel_key"),
                name="unique_editorial_channel_key_per_run",
            ),
        ]
        indexes = [
            models.Index(fields=("run", "status")),
            models.Index(fields=("tv_channel", "status")),
        ]

    def __str__(self):
        return self.name


class EditorialChannelSegment(models.Model):
    channel_candidate = models.ForeignKey(
        "editorial_planning.EditorialChannelCandidate",
        on_delete=models.CASCADE,
        related_name="channel_segments",
    )
    segment = models.ForeignKey(
        "editorial_planning.EditorialSegment",
        on_delete=models.CASCADE,
        related_name="channel_segments",
    )
    role = models.CharField(
        max_length=32,
        choices=EditorialSegmentRole,
        default=EditorialSegmentRole.SECONDARY,
    )
    weight = models.FloatField(default=0.0)
    position = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("position", "-weight", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("channel_candidate", "segment"),
                name="unique_editorial_channel_segment",
            ),
        ]
        indexes = [
            models.Index(fields=("channel_candidate", "role")),
        ]

    def __str__(self):
        return f"{self.channel_candidate.name} / {self.segment.name}"


class EditorialSegmentPath(models.Model):
    channel_candidate = models.OneToOneField(
        "editorial_planning.EditorialChannelCandidate",
        on_delete=models.CASCADE,
        related_name="segment_path",
    )
    is_loop = models.BooleanField(default=True)
    global_score = models.FloatField(default=0.0)
    transition_scores = models.JSONField(default=dict, blank=True)
    diagnostics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.channel_candidate.name} path"


class EditorialSegmentPathElement(models.Model):
    path = models.ForeignKey(
        "editorial_planning.EditorialSegmentPath",
        on_delete=models.CASCADE,
        related_name="elements",
    )
    segment = models.ForeignKey(
        "editorial_planning.EditorialSegment",
        on_delete=models.CASCADE,
        related_name="path_elements",
    )
    position = models.PositiveIntegerField()
    role = models.CharField(
        max_length=32,
        choices=EditorialSegmentRole,
        default=EditorialSegmentRole.SECONDARY,
    )
    reason = models.TextField(blank=True)
    transition_from_previous_score = models.FloatField(default=0.0)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("path", "position"),
                name="unique_editorial_segment_path_position",
            ),
        ]

    def __str__(self):
        return f"{self.path.channel_candidate.name} #{self.position}"


class EditorialPlannedGrid(models.Model):
    channel_candidate = models.OneToOneField(
        "editorial_planning.EditorialChannelCandidate",
        on_delete=models.CASCADE,
        related_name="planned_grid",
    )
    grid_layout = models.OneToOneField(
        "tv_channel.GridLayout",
        on_delete=models.CASCADE,
        related_name="editorial_planning_source",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.channel_candidate.name} / grid #{self.grid_layout_id}"
