from datetime import time

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now

from media_source.constants import MediaContainerKind
from project_ops.constants import AnalyzeStatus


class ChannelProgrammingMode(models.IntegerChoices):
    CLASSIC = 1, "classic"
    MARATHON = 2, "marathon"


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
    programming_mode = models.IntegerField(choices=ChannelProgrammingMode, default=ChannelProgrammingMode.CLASSIC)
    is_enabled = models.BooleanField(default=True)
    analyze_status = models.CharField(max_length=32, choices=AnalyzeStatus, default=AnalyzeStatus.IDLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class EditorialLine(models.Model):
    tv_channel = models.OneToOneField("TvChannel", on_delete=models.CASCADE)

    # dicts keyed by rule axis: categories / natures / container_kinds
    allowed = models.JSONField(default=dict, blank=True)
    preferred = models.JSONField(default=dict, blank=True)
    forbidden = models.JSONField(default=dict, blank=True)

    # diffusion
    start_at = models.TimeField(default=time(6, 0))
    end_at = models.TimeField(default=time(22, 0))
    allow_filler = models.BooleanField(default=True)


class GridLayoutMode(models.IntegerChoices):
    FIXED = 1, "fixed"
    FLEXIBLE = 2, "flexible"
    MARATHON = 3, "marathon"


class GridLayout(models.Model):
    tv_channel = models.ForeignKey("TvChannel", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=now)
    is_active = models.BooleanField(default=False)
    mode = models.IntegerField(choices=GridLayoutMode, default=GridLayoutMode.FIXED)
    post_filler_policy = models.ForeignKey("FillerPolicy", on_delete=models.SET_NULL, blank=True, null=True)

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

    # dicts keyed by rule axis: categories / natures / container_kinds
    allowed = models.JSONField(default=dict, blank=True)
    preferred = models.JSONField(default=dict, blank=True)
    forbidden = models.JSONField(default=dict, blank=True)

    post_filler_policy = models.ForeignKey("FillerPolicy", on_delete=models.SET_NULL, blank=True, null=True)


class MarathonConfig(models.Model):
    grid_layout = models.OneToOneField(
        "GridLayout",
        on_delete=models.CASCADE,
        related_name="marathon_config",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Marathon config grid #{self.grid_layout_id}"


class MarathonKindPolicy(models.Model):
    """
    Rotation contract for one container kind: a kind absent from the config
    (or with max_run=0) is excluded from the marathon rotation even if the
    editorial line matches it.
    """
    config = models.ForeignKey(
        "MarathonConfig",
        on_delete=models.CASCADE,
        related_name="kind_policies",
    )
    container_kind = models.IntegerField(choices=MediaContainerKind)
    min_run = models.PositiveIntegerField(default=1)  # ne pas lancer un container avec moins de N items
    max_run = models.PositiveIntegerField(default=1)  # nb d'items enchaines vise; 0 = kind desactive
    quota = models.PositiveIntegerField(default=1)  # poids de rotation entre kinds

    class Meta:
        ordering = ("container_kind", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("config", "container_kind"),
                name="unique_marathon_kind_policy_per_config",
            ),
        ]

    def clean(self):
        if self.max_run and self.min_run > self.max_run:
            raise ValidationError("min_run must be <= max_run.")
        if self.max_run and self.quota < 1:
            raise ValidationError("quota must be >= 1 for an enabled kind.")

    def __str__(self):
        return f"{self.get_container_kind_display()} run {self.min_run}-{self.max_run} quota {self.quota}"


class FillerPolicyManager(models.Manager):
    def get_or_create_for_params(self, duration_seconds: int = 180, allowed_roles: list | None = None) -> "FillerPolicy":
        """
        Return an existing policy with these behavioral params, or create one.

        There is no unique constraint on (duration_seconds, allowed_roles):
        databases predating the reuse may hold duplicates, so the oldest match
        wins. Duplicates from concurrent creations are harmless since every
        consumer only reads duration_seconds/allowed_roles.
        """
        allowed_roles = sorted(allowed_roles or [])
        policy = (
            self.filter(duration_seconds=duration_seconds, allowed_roles=allowed_roles)
            .order_by("id")
            .first()
        )
        if policy is not None:
            return policy
        roles_label = ", ".join(allowed_roles) if allowed_roles else "default roles"
        return self.create(
            name=f"Post-roll {duration_seconds}s ({roles_label})"[:80],
            duration_seconds=duration_seconds,
            allowed_roles=allowed_roles,
        )


class FillerPolicy(models.Model):
    """
    The slot for fillers: a post-roll window of duration_seconds filled with
    content from collections whose programming_role is in allowed_roles
    (labels of MediaProgrammingRole; empty means ["trailer", "filler"]).
    """
    name = models.CharField(max_length=80)
    duration_seconds = models.PositiveIntegerField(default=180)
    allowed_roles = models.JSONField(default=list, blank=True)

    objects = FillerPolicyManager()

    def __str__(self):
        return self.name
