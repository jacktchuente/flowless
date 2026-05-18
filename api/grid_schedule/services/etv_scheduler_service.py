from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError

from etv_scripted_schedule_api import ScriptedScheduleClient, ContentSearch, PlayoutCount, PlayoutPadUntilExact, \
    ControlGraphicsOn, ControlGraphicsOff
from grid_schedule.models import ScheduleMediaItem
from media_source.constants import MediaContainerKind
from tv_channel.models import TvChannel


@dataclass
class ETVSchedulerResult:
    tv_channel: TvChannel
    api_host: str
    loop_items: list[dict]

    def to_dict(self) -> dict:
        return {
            "channel_id": self.tv_channel.id,
            "channel_key": str(self.tv_channel.pk),
            "channel_name": self.tv_channel.name,
            "api_host": self.api_host,
            "items": self.loop_items,
        }


class ETVSchedulerService:
    def __init__(self, *, channel_key: str, build_id: str | int, mode: str | None = None, profile: str | None = None):
        self.channel_key = channel_key
        self.build_id = build_id
        self.mode = mode
        self.profile = profile
        self.api_host = getattr(settings, "ETV_BASE_URL", "").rstrip("/")

    def run3(self) -> ETVSchedulerResult:
        if not self.api_host:
            raise ValidationError("ETV_BASE_URL is not configured.")

        etv_scripted_client = ScriptedScheduleClient(
            host_url=self.api_host,
            build_id=str(self.build_id),
        )

        context = etv_scripted_client.get_context()
        tv_channel = self._get_tv_channel()

        filler_key = "filler-test"

        etv_scripted_client.add_search(
            ContentSearch(
                key=filler_key,
                query='show_tag:trailer AND show_tag:show AND type:episode AND minutes:[0 TO 3]',
                order="shuffle",
            )
        )

        etv_scripted_client.graphics_on(
            ControlGraphicsOn(
                graphics=["subtitle/ticker.yml"],
                variables={
                    "show_name": "TEST FILLER",
                },
            )
        )

        etv_scripted_client.add_count(
            PlayoutCount(
                content=filler_key,
                count=10,
                customTitle="TEST FILLER",
            )
        )

        etv_scripted_client.graphics_off(
            ControlGraphicsOff(
                graphics=["subtitle/ticker.yml"],
            )
        )

        return ETVSchedulerResult(
            tv_channel=tv_channel,
            api_host=self.api_host,
            loop_items=[],
        )

    def run(self) -> ETVSchedulerResult:
        if not self.api_host:
            raise ValidationError("ETV_BASE_URL is not configured.")

        etv_scripted_client = ScriptedScheduleClient(host_url=self.api_host, build_id=str(self.build_id))
        context = etv_scripted_client.get_context()
        tv_channel = self._get_tv_channel()
        loop_items = self._build_loop_items(tv_channel, context.startTime, context.finishTime)

        filler_key = "filler"

        etv_scripted_client.add_search(
            ContentSearch(
                key=filler_key,
                query='show_tag:trailer AND show_tag:show AND type:episode AND minutes:[0 TO 3]',
                order="shuffle",
            )
        )

        for element in loop_items:
            key = element.get('schedule_media_item_id', str(uuid4()))
            query = self._get_query(element)
            starts_at = element.get("starts_at")
            if not query:
                continue
            etv_scripted_client.add_search(ContentSearch(
                key=key,
                query=query))
            etv_scripted_client.pad_until_exact(
                PlayoutPadUntilExact(
                    content=filler_key,
                    when=starts_at,
                    fallback=filler_key,
                    trim=True,
                    stopBeforeEnd=True,
                    fillerKind="Tail",
                    customTitle="Interlude",
                )
            )
            etv_scripted_client.add_count(
                PlayoutCount(
                    content=key,
                    count=1,
                    customTitle=element.get("media_item_title"),
                )
            )
        return ETVSchedulerResult(
            tv_channel=tv_channel,
            api_host=self.api_host,
            loop_items=loop_items,
        )

    def _get_tv_channel(self) -> TvChannel:
        return TvChannel.objects.select_related("catalog").get(pk=self.channel_key)

    @staticmethod
    def _build_loop_items(tv_channel: TvChannel, start_at: str, ends_at: str) -> list[dict]:
        queryset = (
            ScheduleMediaItem.objects
            .filter(
                block_container_selection__tv_playout__tv_channel=tv_channel,
                block_container_selection__tv_playout__is_active=True,
                item__is_missing=False,
                starts_at__gte=start_at,
                ends_at__lte=ends_at,
            )
            .select_related(
                "item",
                "item__container",
                "item__container__media_collection",
                "block_container_selection",
                "block_container_selection__block",
            )
            .order_by("starts_at", "item__season_number", "item__episode_number", "item__sequence_number", "id")
        )

        return [
            {
                "schedule_media_item_id": scheduled.id,
                "media_item_id": scheduled.item_id,
                "media_item_external_id": scheduled.item.external_id,
                "media_item_title": scheduled.item.title,
                "media_container_id": scheduled.item.container_id,
                "media_container_external_id": scheduled.item.container.external_id,
                "media_container_title": scheduled.item.container.title,
                "block_id": scheduled.block_container_selection.block_id,
                "block_name": ETVSchedulerService._block_label(scheduled.block_container_selection.block),
                "starts_at": scheduled.starts_at.isoformat(),
                "ends_at": scheduled.ends_at.isoformat(),
                "duration_seconds": scheduled.item.duration_seconds,
                "season_number": scheduled.item.season_number,
                "episode_number": scheduled.item.episode_number,
                "sequence_number": scheduled.item.sequence_number,
                "media_container_kind": getattr(scheduled.item.container.media_collection, "container_kind", None),
            }
            for scheduled in queryset
        ]

    @staticmethod
    def _get_query(element):
        container_kind = element.get("media_container_kind")
        title = ETVSchedulerService._escape_query_value(element.get("media_container_title") or "")
        if not title:
            return None
        if container_kind == MediaContainerKind.STANDALONE_VIDEO:
            return f'title:"{title}" AND type:movie'
        if container_kind == MediaContainerKind.SERIES:
            episode_number = element.get("episode_number")
            season_number = element.get("season_number")
            if episode_number is not None and season_number is not None:
                return f'show_title:"{title}" AND type:episode AND episode_number:{episode_number} AND season_number:{season_number}'
            return f'show_title:"{title}" AND type:episode'
        return f'title:"{title}"'

    @staticmethod
    def _escape_query_value(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').strip()

    @staticmethod
    def _block_label(block) -> str:
        return f"{block.starts_at.strftime('%H:%M')}-{block.ends_at.strftime('%H:%M')}"
