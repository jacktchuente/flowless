from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class ApiResult:
    payload: JsonDict


@dataclass(frozen=True)
class ChannelInput:
    name: str
    number: str
    ffmpeg_profile_id: int
    group: str = "ErsatzTV"
    categories: str | None = None
    slug_seconds: float | None = None
    logo_path: str | None = None
    logo_content_type: str | None = None
    stream_selector_mode: str = "Default"
    stream_selector: str | None = None
    preferred_audio_language_code: str | None = None
    preferred_audio_title: str | None = None
    playout_source: str = "Generated"
    playout_mode: str = "Continuous"
    mirror_source_channel_id: int | None = None
    playout_offset_hours: int | None = None
    streaming_mode: str = "TransportStreamHybrid"
    watermark_id: int | None = None
    fallback_filler_id: int | None = None
    preferred_subtitle_language_code: str | None = None
    subtitle_mode: str = "None"
    music_video_credits_mode: str = "None"
    music_video_credits_template: str | None = None
    song_video_mode: str = "Default"
    transcode_mode: str = "OnDemand"
    idle_behavior: str = "StopOnDisconnect"
    is_enabled: bool = True
    show_in_epg: bool = True

    def to_api_payload(self) -> JsonDict:
        return {
            "name": self.name,
            "number": self.number,
            "group": self.group,
            "categories": self.categories,
            "ffmpegProfileId": self.ffmpeg_profile_id,
            "slugSeconds": self.slug_seconds,
            "logoPath": self.logo_path,
            "logoContentType": self.logo_content_type,
            "streamSelectorMode": self.stream_selector_mode,
            "streamSelector": self.stream_selector,
            "preferredAudioLanguageCode": self.preferred_audio_language_code,
            "preferredAudioTitle": self.preferred_audio_title,
            "playoutSource": self.playout_source,
            "playoutMode": self.playout_mode,
            "mirrorSourceChannelId": self.mirror_source_channel_id,
            "playoutOffsetHours": self.playout_offset_hours,
            "streamingMode": self.streaming_mode,
            "watermarkId": self.watermark_id,
            "fallbackFillerId": self.fallback_filler_id,
            "preferredSubtitleLanguageCode": self.preferred_subtitle_language_code,
            "subtitleMode": self.subtitle_mode,
            "musicVideoCreditsMode": self.music_video_credits_mode,
            "musicVideoCreditsTemplate": self.music_video_credits_template,
            "songVideoMode": self.song_video_mode,
            "transcodeMode": self.transcode_mode,
            "idleBehavior": self.idle_behavior,
            "isEnabled": self.is_enabled,
            "showInEpg": self.show_in_epg,
        }


@dataclass(frozen=True)
class ChannelUpsertRequest:
    channel: ChannelInput
    logo_file: Path | None = None


@dataclass(frozen=True)
class ScriptedPlayoutInput:
    channel_id: int
    schedule_file: str = ""

    def to_api_payload(self) -> JsonDict:
        return {"channelId": self.channel_id, "scheduleFile": self.schedule_file}


@dataclass(frozen=True)
class ScriptedPlayoutUpsertRequest:
    playout: ScriptedPlayoutInput
    schedule_upload: Path | None = None


@dataclass(frozen=True)
class ExternalIdLookupInput:
    media_type: str
    external_id: str
    source: str = "metadata_guid"

    def to_api_payload(self) -> dict[str, str]:
        return {
            "source": self.source,
            "mediaType": self.media_type,
            "externalId": self.external_id,
        }


@dataclass(frozen=True)
class ExternalIdLookupOutput:
    source: str
    media_type: str
    external_id: str
    found: bool
    internal_id: int | None
    metadata_id: int | None

    @classmethod
    def from_api_payload(cls, payload: JsonDict) -> ExternalIdLookupOutput:
        return cls(
            source=str(payload["source"]),
            media_type=str(payload["mediaType"]),
            external_id=str(payload["externalId"]),
            found=bool(payload["found"]),
            internal_id=payload.get("internalId"),
            metadata_id=payload.get("metadataId"),
        )
