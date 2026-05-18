from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings

from iptv_player.services.etv_client import (
    ChannelInput,
    ChannelUpsertRequest,
    EtvClient,
    ScriptedPlayoutInput,
    ScriptedPlayoutUpsertRequest,
)
from tv_channel.models import TvChannel


@dataclass(frozen=True)
class EtvChannelPushResult:
    mode: str
    etv_channel_id: int | None
    payload: dict[str, Any]


class EtvChannelPushService:
    def __init__(self, tv_channel: TvChannel) -> None:
        self.tv_channel = tv_channel
        self.client = EtvClient(base_url=settings.ETV_API_BASE_URL)

    def run(self) -> EtvChannelPushResult:
        ffmpeg_profile_id = self._resolve_ffmpeg_profile_id()
        channel_request = ChannelUpsertRequest(
            channel=ChannelInput(
                name=self.tv_channel.name,
                number=str(self.tv_channel.id),
                ffmpeg_profile_id=ffmpeg_profile_id,
                group=self._resolve_channel_group(),
            ),
            logo_file=self._get_logo_file(),
        )

        existing_channel = self._find_existing_channel()
        if existing_channel is None:
            channel_payload = self.client.create_channel(channel_request).payload
            channel_mode = "create"
            etv_channel_id = self._extract_channel_id(channel_payload)
        else:
            etv_channel_id = self._extract_channel_id(existing_channel)
            if etv_channel_id is None:
                raise ValueError(
                    f"ErsatzTV returned a channel matching tv_channel_id={self.tv_channel.id} without a usable id."
                )
            channel_payload = self.client.update_channel(etv_channel_id, channel_request).payload
            channel_mode = "update"

        if etv_channel_id is None:
            raise ValueError(f"ErsatzTV returned no usable channel id for tv_channel_id={self.tv_channel.id}.")

        playout_mode, playout_payload = self._upsert_scripted_playout(etv_channel_id)
        playout_id = self._extract_playout_id(playout_payload)
        if playout_id is not None:
            self._persist_external_playout_id(playout_id)

        return EtvChannelPushResult(
            mode=channel_mode,
            etv_channel_id=etv_channel_id,
            payload={
                "channel": channel_payload,
                "scripted_playout": {
                    "mode": playout_mode,
                    "payload": playout_payload,
                },
            },
        )

    def _upsert_scripted_playout(self, etv_channel_id: int) -> tuple[str, dict[str, Any]]:
        request = ScriptedPlayoutUpsertRequest(
            playout=ScriptedPlayoutInput(
                channel_id=etv_channel_id,
                schedule_file=f"{settings.ETV_API_WRAPPER_FILE_PATH} {self.tv_channel.id}",
            )
        )

        if not self.tv_channel.external_playout_id:
            return "create", self.client.create_scripted_playout(request).payload

        return "update", self.client.update_scripted_playout(int(self.tv_channel.external_playout_id), request).payload

    def _resolve_ffmpeg_profile_id(self) -> int:
        try:
            payload = self.client.list_ffmpeg_profiles().payload
            profiles = self._extract_collection(payload)
            if not profiles:
                raise ValueError("ErsatzTV returned no FFmpeg profile.")
            profile_id = profiles[0].get("id")
            if profile_id is None:
                raise ValueError("ErsatzTV FFmpeg profile payload is missing an id.")
            return int(profile_id)
        except Exception:
            return 1

    def _find_existing_channel(self) -> dict[str, Any] | None:
        payload = self.client.list_channels().payload
        channels = self._extract_collection(payload)

        expected_number = str(self.tv_channel.id)
        for channel in channels:
            if str(channel.get("number", "")) == expected_number:
                return channel

        expected_name = self.tv_channel.name
        for channel in channels:
            if str(channel.get("name", "")) == expected_name:
                return channel

        return None

    def _persist_external_playout_id(self, playout_id: int) -> None:
        external_playout_id = str(playout_id)
        if self.tv_channel.external_playout_id == external_playout_id:
            return
        self.tv_channel.external_playout_id = external_playout_id
        self.tv_channel.save(update_fields=["external_playout_id", "updated_at"])

    def _get_logo_file(self) -> Path | None:
        if not self.tv_channel.logo:
            return None
        logo_path = getattr(self.tv_channel.logo, "path", None)
        if not logo_path:
            return None
        path = Path(logo_path)
        return path if path.exists() else None

    def _resolve_channel_group(self) -> str:
        catalog = getattr(self.tv_channel, "catalog", None)
        catalog_name = getattr(catalog, "name", None)
        if catalog_name:
            return str(catalog_name)
        return "ErsatzTV"

    @staticmethod
    def _extract_collection(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("items", "results", "data", "channels", "playouts"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _extract_channel_id(payload: Any) -> int | None:
        if isinstance(payload, dict):
            for key in ("id", "channelId"):
                value = payload.get(key)
                if value is not None:
                    return int(value)
        return None

    @classmethod
    def _extract_playout_id(cls, payload: Any) -> int | None:
        if isinstance(payload, dict):
            for key in ("id", "playoutId"):
                value = payload.get(key)
                if value is not None:
                    return int(value)
        return None
