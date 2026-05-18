from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

import requests

from .models import (
    ApiResult,
    ChannelUpsertRequest,
    ExternalIdLookupInput,
    ExternalIdLookupOutput,
    JsonDict,
    ScriptedPlayoutUpsertRequest,
)


class EtvClient:
    def __init__(self, base_url: str, timeout: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> ApiResult:
        return ApiResult(self._request("GET", "/health"))

    def list_ffmpeg_profiles(self) -> ApiResult:
        return ApiResult(self._request("GET", "/ffmpeg-profiles"))

    def list_channels(self) -> ApiResult:
        return ApiResult(self._request("GET", "/channels"))

    def get_channel(self, channel_id: int) -> ApiResult:
        return ApiResult(self._request("GET", f"/channels/{channel_id}"))

    def create_channel(self, request: ChannelUpsertRequest) -> ApiResult:
        return ApiResult(self._channel_upsert("POST", "/channels", request))

    def update_channel(self, channel_id: int, request: ChannelUpsertRequest) -> ApiResult:
        return ApiResult(self._channel_upsert("PUT", f"/channels/{channel_id}", request))

    def delete_channel(self, channel_id: int) -> ApiResult:
        return ApiResult(self._request("DELETE", f"/channels/{channel_id}"))

    def reset_channel_playout(self, channel_number: str) -> ApiResult:
        return ApiResult(self._request("POST", f"/channels/{channel_number}/playout/reset"))

    def reboot_channel(self, channel_id: int) -> ApiResult:
        return ApiResult(self._request("POST", f"/channels/{channel_id}/reboot"))

    def reset_channel_playout_by_id(self, channel_id: int) -> ApiResult:
        return ApiResult(self._request("POST", f"/channels/{channel_id}/playout/reset"))

    def list_playouts(self, query: str = "") -> ApiResult:
        params = {"query": query} if query else None
        return ApiResult(self._request("GET", "/playouts", params=params))

    def get_playout(self, playout_id: int) -> ApiResult:
        return ApiResult(self._request("GET", f"/playouts/{playout_id}"))

    def create_scripted_playout(self, request: ScriptedPlayoutUpsertRequest) -> ApiResult:
        return ApiResult(self._scripted_playout_upsert("POST", "/playouts/scripted", request))

    def update_scripted_playout(self, playout_id: int, request: ScriptedPlayoutUpsertRequest) -> ApiResult:
        return ApiResult(
            self._scripted_playout_upsert("PUT", f"/playouts/scripted/{playout_id}", request)
        )

    def delete_playout(self, playout_id: int) -> ApiResult:
        return ApiResult(self._request("DELETE", f"/playouts/{playout_id}"))

    def resolve_external_id(self, item: ExternalIdLookupInput) -> ExternalIdLookupOutput:
        payload = self._request("GET", "/media-items/resolve-external-id", params=item.to_api_payload())
        results = payload.get("results", [])
        if len(results) != 1:
            raise ValueError(f"Expected exactly one result, received {len(results)}")

        return ExternalIdLookupOutput.from_api_payload(results[0])

    def resolve_external_ids(self, items: list[ExternalIdLookupInput]) -> list[ExternalIdLookupOutput]:
        payload = self._request(
            "POST",
            "/media-items/resolve-external-ids",
            json_body={"items": [item.to_api_payload() for item in items]},
        )
        results = payload.get("results", [])
        return [ExternalIdLookupOutput.from_api_payload(result) for result in results]

    def _channel_upsert(self, method: str, path: str, request: ChannelUpsertRequest) -> JsonDict:
        if request.logo_file is None:
            return self._request(method, path, json_body=request.channel.to_api_payload())

        data = {"payload": json.dumps(request.channel.to_api_payload())}
        files = {"logo": self._build_file_tuple(request.logo_file)}
        return self._request(method, path, data=data, files=files)

    def _scripted_playout_upsert(
        self,
        method: str,
        path: str,
        request: ScriptedPlayoutUpsertRequest,
    ) -> JsonDict:
        if request.schedule_upload is None:
            return self._request(method, path, json_body=request.playout.to_api_payload())

        data = {"payload": json.dumps(request.playout.to_api_payload())}
        files = {"schedule": self._build_file_tuple(request.schedule_upload)}
        return self._request(method, path, data=data, files=files)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: JsonDict | None = None,
        data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> JsonDict:
        response = requests.request(
            method=method,
            url=f"{self.base_url}{path}",
            params=params,
            json=json_body,
            data=data,
            files=files,
            timeout=self.timeout,
        )
        print(response.json())
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _build_file_tuple(path: Path) -> tuple[str, bytes, str]:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return (path.name, path.read_bytes(), content_type)
