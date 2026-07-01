from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from editorial_planning.models import (
    EditorialChannelCandidate,
    EditorialChannelCandidateStatus,
    EditorialPlannedGrid,
)
from tv_channel.models import EditorialLine, FillerPolicy, GridLayout, GridLayoutMode, TvChannel


class EditorialFlexibleChannelCreationService:
    def __init__(self, *, channel_candidate: EditorialChannelCandidate):
        self.channel_candidate = channel_candidate

    def create_channel(self, *, name: str | None = None, activate_grid: bool = True) -> TvChannel:
        if not hasattr(self.channel_candidate, "segment_path"):
            raise ValidationError("Editorial channel candidate must have a segment path.")

        channel_name = (name or self.channel_candidate.name).strip()
        if not channel_name:
            raise ValidationError("Channel name is required.")
        if TvChannel.objects.filter(name=channel_name).exists():
            raise ValidationError("Channel name already exists.")

        with transaction.atomic():
            tv_channel = TvChannel.objects.create(
                name=channel_name[:50],
                description=self.channel_candidate.description or "",
                specification=self._build_specification(),
                catalog=self.channel_candidate.run.catalog,
            )
            EditorialLine.objects.create(
                tv_channel=tv_channel,
                allowed_categories=self._dominant_categories(),
                preferred_categories=self._dominant_categories(),
                allowed_natures=self._dominant_natures(),
                preferred_natures=self._dominant_natures(),
                allow_filler=True,
            )
            if activate_grid:
                GridLayout.objects.filter(tv_channel=tv_channel, is_active=True).update(is_active=False)
            filler_policy = FillerPolicy.objects.create(name=f"{tv_channel.name} - flexible")
            grid_layout = GridLayout.objects.create(
                tv_channel=tv_channel,
                is_active=activate_grid,
                mode=GridLayoutMode.FLEXIBLE,
                post_filler_policy=filler_policy,
            )
            EditorialPlannedGrid.objects.create(
                channel_candidate=self.channel_candidate,
                grid_layout=grid_layout,
            )
            self.channel_candidate.tv_channel = tv_channel
            self.channel_candidate.status = EditorialChannelCandidateStatus.SELECTED
            self.channel_candidate.save(update_fields=["tv_channel", "status", "updated_at"])
            return tv_channel

    def _build_specification(self) -> str:
        profile = self.channel_candidate.profile or {}
        categories = ", ".join(profile.get("dominant_categories") or [])
        nature = profile.get("dominant_nature") or ""
        parts = ["Flexible editorial flow channel."]
        if nature:
            parts.append(f"Dominant nature: {nature}.")
        if categories:
            parts.append(f"Dominant categories: {categories}.")
        return " ".join(parts)

    def _dominant_categories(self) -> list[str]:
        values = self.channel_candidate.profile.get("dominant_categories") if self.channel_candidate.profile else []
        return [value for value in (values or []) if isinstance(value, str)]

    def _dominant_natures(self) -> list:
        value = self.channel_candidate.profile.get("dominant_nature") if self.channel_candidate.profile else None
        if value is None:
            return []
        return [value]
