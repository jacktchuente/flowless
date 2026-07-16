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
                allowed={
                    "categories": self._dominant_categories(),
                    "natures": self._dominant_natures(),
                },
                preferred={
                    "categories": self._dominant_categories(),
                    "natures": self._dominant_natures(),
                },
                allow_filler=True,
            )
            if activate_grid:
                GridLayout.objects.filter(tv_channel=tv_channel, is_active=True).update(is_active=False)
            filler_policy = FillerPolicy.objects.get_or_create_for_params()
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

    DURATION_BUCKET_LABELS = {
        "very_short": "formats très courts (<5 min)",
        "short": "formats courts (5-15 min)",
        "tv_short": "épisodes ~30 min",
        "medium_episode": "épisodes ~45 min",
        "long_episode": "épisodes ~1h",
        "film_length": "films",
        "very_long": "formats longs (>2h)",
    }

    def _build_specification(self) -> str:
        profile = self.channel_candidate.profile or {}
        segments = list(
            self.channel_candidate.channel_segments
            .select_related("segment")
            .order_by("position", "-weight")
        )

        lines = ["Chaîne flexible générée automatiquement depuis la bibliothèque (flow éditorial bottom-up)."]

        nature = profile.get("dominant_nature")
        if nature:
            lines.append(f"Nature dominante : {nature}.")
        categories = [value for value in (profile.get("dominant_categories") or []) if value]
        if categories:
            lines.append(f"Catégories dominantes : {', '.join(categories)}.")

        segment_profiles = [channel_segment.segment.profile or {} for channel_segment in segments]
        formats = self._collect_values(segment_profiles, "duration_bucket")
        if formats:
            labels = [self.DURATION_BUCKET_LABELS.get(value, value) for value in formats]
            lines.append(f"Formats : {', '.join(dict.fromkeys(labels))}.")
        decades = sorted({value for p in segment_profiles for value in (p.get("decades") or [])})
        if decades:
            lines.append(f"Époques couvertes : {', '.join(decades)}.")
        anime_values = self._collect_values(segment_profiles, "dominant_anime")
        if anime_values == ["anime"]:
            lines.append("Contenu anime.")
        elif "anime" in anime_values:
            lines.append("Contenu partiellement anime.")
        age_values = self._collect_values(segment_profiles, "dominant_age_bucket")
        if age_values:
            lines.append(f"Public : {', '.join(age_values)}.")

        if segments:
            lines.append(f"Composée de {len(segments)} segment(s) éditoriaux :")
            for channel_segment in segments:
                segment = channel_segment.segment
                lines.append(
                    f"- {segment.name} (rôle {channel_segment.role}, {segment.media_count} médias)"
                )

        return "\n".join(lines)

    @staticmethod
    def _collect_values(profiles: list[dict], key: str) -> list[str]:
        values: list[str] = []
        for profile in profiles:
            value = profile.get(key)
            if value and value != "unknown" and value not in values:
                values.append(value)
        return values

    def _dominant_categories(self) -> list[str]:
        values = self.channel_candidate.profile.get("dominant_categories") if self.channel_candidate.profile else []
        return [value for value in (values or []) if isinstance(value, str)]

    def _dominant_natures(self) -> list:
        value = self.channel_candidate.profile.get("dominant_nature") if self.channel_candidate.profile else None
        if value is None:
            return []
        return [value]
