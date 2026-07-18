from __future__ import annotations

from dataclasses import dataclass
import logging

from django.conf import settings
from django.core.files.base import ContentFile

from project_ops.constants import AnalyzeStatus
from tv_channel.models import ChannelImageKind, ChannelImageSuggestion, ChannelImageSuggestionRun, TvChannel
from tv_channel.services.image_suggestion.query_service import ChannelImageQueryService, ImageQueryError
from tv_channel.services.image_suggestion.search import collect_image_results, get_provider

logger = logging.getLogger(__name__)


@dataclass
class SuggestionRunResult:
    run: ChannelImageSuggestionRun
    suggestion_count: int
    warnings: list[str]


class ChannelImageSuggestionService:
    def __init__(self, tv_channel: TvChannel):
        self.tv_channel = tv_channel

    def run(
        self,
        *,
        kind: int = ChannelImageKind.LOGO,
        query: str | None = None,
        entity_type: str | None = None,
    ) -> SuggestionRunResult:
        run = ChannelImageSuggestionRun.objects.create(
            tv_channel=self.tv_channel,
            kind=kind,
            status=AnalyzeStatus.ANALYZING,
        )
        warnings: list[str] = []
        try:
            image_query = ChannelImageQueryService(self.tv_channel).resolve(
                query=query,
                entity_type=entity_type,
            )
            run.entity_type = image_query.entity_type
            run.query = image_query.query
            run.query_source = image_query.source
            run.save(update_fields=["entity_type", "query", "query_source", "updated_at"])

            limit = int(getattr(settings, "CHANNEL_IMAGE_SUGGESTION_COUNT", 5))
            results, warnings = collect_image_results(self.tv_channel, image_query, limit)
            created = self._store_suggestions(run, results, warnings)
            if created == 0:
                warnings.append("No image suggestion found.")

            run.status = (
                AnalyzeStatus.COMPLETE if created and not warnings else AnalyzeStatus.COMPLETE_WITH_ERRORS
            )
            run.diagnostics = {"warnings": warnings}
            run.save(update_fields=["status", "diagnostics", "updated_at"])
        except ImageQueryError as exc:
            warnings.append(str(exc))
            run.status = AnalyzeStatus.COMPLETE_WITH_ERRORS
            run.diagnostics = {"warnings": warnings}
            run.save(update_fields=["status", "diagnostics", "updated_at"])
        self._purge_old_runs(kind=kind)
        return SuggestionRunResult(run=run, suggestion_count=run.suggestions.count(), warnings=warnings)

    def _store_suggestions(self, run: ChannelImageSuggestionRun, results, warnings: list[str]) -> int:
        position = 0
        for result in results:
            provider = get_provider(self.tv_channel, result.provider)
            if provider is None:
                warnings.append(f"Unknown image provider {result.provider}.")
                continue
            try:
                thumbnail_bytes = provider.download(result.thumbnail_url)
            except Exception as exc:
                logger.exception("Thumbnail download failed url=%s", result.thumbnail_url)
                warnings.append(f"Thumbnail download failed for {result.thumbnail_url}: {exc}")
                continue
            position += 1
            suggestion = ChannelImageSuggestion(
                run=run,
                position=position,
                provider=result.provider,
                source_url=result.source_url,
                width=result.width,
                height=result.height,
                attribution=result.attribution[:255],
            )
            suggestion.thumbnail.save(
                f"run_{run.id}_{position}.img",
                ContentFile(thumbnail_bytes),
                save=False,
            )
            suggestion.save()
        return position

    def _purge_old_runs(self, *, kind: int) -> None:
        kept = int(getattr(settings, "CHANNEL_IMAGE_RUNS_KEPT", 5))
        old_runs = ChannelImageSuggestionRun.objects.filter(
            tv_channel=self.tv_channel,
            kind=kind,
        ).order_by("-created_at", "-id")[kept:]
        for run in old_runs:
            for suggestion in run.suggestions.all():
                if suggestion.thumbnail:
                    suggestion.thumbnail.delete(save=False)
            run.delete()
