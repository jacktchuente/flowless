"""HTTP client for the ErsatzTV scripted schedule API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Type, Union
from urllib.parse import quote

import requests

from .models import (
    BaseModel,
    ContentAll,
    ContentCollection,
    ContentCreatePlaylist,
    ContentMarathon,
    ContentMultiCollection,
    ContentPlaylist,
    ContentSearch,
    ContentShow,
    ContentSmartCollection,
    ControlGraphicsOff,
    ControlGraphicsOn,
    ControlPreRollOn,
    ControlSkipItems,
    ControlSkipToItem,
    ControlStartEpgGroup,
    ControlWaitUntil,
    ControlWaitUntilExact,
    ControlWatermarkOff,
    ControlWatermarkOn,
    PeekItemDuration,
    PlayoutContext,
    PlayoutCount,
    PlayoutDuration,
    PlayoutPadToNext,
    PlayoutPadUntil,
    PlayoutPadUntilExact,
)

Payload = Union[BaseModel, Mapping[str, Any]]
QueryParams = Optional[Mapping[str, Any]]


class ErsatzTVAPIError(RuntimeError):
    """Raised when the API returns a non-success response."""

    def __init__(self, *, method: str, url: str, status_code: int, response_text: str) -> None:
        self.method = method
        self.url = url
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(f"{method} {url} returned HTTP {status_code}: {response_text[:500]}")


@dataclass(frozen=True)
class EndpointSpec:
    """Documents the input/output object expected by an endpoint."""

    method_name: str
    http_method: str
    path: str
    payload_model: Optional[Type[BaseModel]]
    response_model: Optional[Type[BaseModel]]


ENDPOINTS: Dict[str, EndpointSpec] = {
    "get_context": EndpointSpec(
        "get_context", "GET", "/api/scripted/playout/build/{buildId}/context", None, PlayoutContext
    ),
    "add_collection": EndpointSpec(
        "add_collection", "POST", "/api/scripted/playout/build/{buildId}/add_collection", ContentCollection, None
    ),
    "add_marathon": EndpointSpec(
        "add_marathon", "POST", "/api/scripted/playout/build/{buildId}/add_marathon", ContentMarathon, None
    ),
    "add_multi_collection": EndpointSpec(
        "add_multi_collection",
        "POST",
        "/api/scripted/playout/build/{buildId}/add_multi_collection",
        ContentMultiCollection,
        None,
    ),
    "add_playlist": EndpointSpec(
        "add_playlist", "POST", "/api/scripted/playout/build/{buildId}/add_playlist", ContentPlaylist, None
    ),
    "create_playlist": EndpointSpec(
        "create_playlist",
        "POST",
        "/api/scripted/playout/build/{buildId}/create_playlist",
        ContentCreatePlaylist,
        None,
    ),
    "add_search": EndpointSpec(
        "add_search", "POST", "/api/scripted/playout/build/{buildId}/add_search", ContentSearch, None
    ),
    "add_smart_collection": EndpointSpec(
        "add_smart_collection",
        "POST",
        "/api/scripted/playout/build/{buildId}/add_smart_collection",
        ContentSmartCollection,
        None,
    ),
    "add_show": EndpointSpec(
        "add_show", "POST", "/api/scripted/playout/build/{buildId}/add_show", ContentShow, None
    ),
    "add_all": EndpointSpec(
        "add_all", "POST", "/api/scripted/playout/build/{buildId}/add_all", ContentAll, PlayoutContext
    ),
    "add_count": EndpointSpec(
        "add_count", "POST", "/api/scripted/playout/build/{buildId}/add_count", PlayoutCount, PlayoutContext
    ),
    "add_duration": EndpointSpec(
        "add_duration", "POST", "/api/scripted/playout/build/{buildId}/add_duration", PlayoutDuration, PlayoutContext
    ),
    "pad_to_next": EndpointSpec(
        "pad_to_next", "POST", "/api/scripted/playout/build/{buildId}/pad_to_next", PlayoutPadToNext, PlayoutContext
    ),
    "pad_until": EndpointSpec(
        "pad_until", "POST", "/api/scripted/playout/build/{buildId}/pad_until", PlayoutPadUntil, PlayoutContext
    ),
    "pad_until_exact": EndpointSpec(
        "pad_until_exact",
        "POST",
        "/api/scripted/playout/build/{buildId}/pad_until_exact",
        PlayoutPadUntilExact,
        PlayoutContext,
    ),
    "peek_next": EndpointSpec(
        "peek_next", "GET", "/api/scripted/playout/build/{buildId}/peek_next/{content}", None, PeekItemDuration
    ),
    "start_epg_group": EndpointSpec(
        "start_epg_group",
        "POST",
        "/api/scripted/playout/build/{buildId}/start_epg_group",
        ControlStartEpgGroup,
        None,
    ),
    "stop_epg_group": EndpointSpec(
        "stop_epg_group", "POST", "/api/scripted/playout/build/{buildId}/stop_epg_group", None, None
    ),
    "graphics_on": EndpointSpec(
        "graphics_on", "POST", "/api/scripted/playout/build/{buildId}/graphics_on", ControlGraphicsOn, None
    ),
    "graphics_off": EndpointSpec(
        "graphics_off", "POST", "/api/scripted/playout/build/{buildId}/graphics_off", ControlGraphicsOff, None
    ),
    "watermark_on": EndpointSpec(
        "watermark_on", "POST", "/api/scripted/playout/build/{buildId}/watermark_on", ControlWatermarkOn, None
    ),
    "watermark_off": EndpointSpec(
        "watermark_off", "POST", "/api/scripted/playout/build/{buildId}/watermark_off", ControlWatermarkOff, None
    ),
    "pre_roll_on": EndpointSpec(
        "pre_roll_on", "POST", "/api/scripted/playout/build/{buildId}/pre_roll_on", ControlPreRollOn, None
    ),
    "pre_roll_off": EndpointSpec(
        "pre_roll_off", "POST", "/api/scripted/playout/build/{buildId}/pre_roll_off", None, None
    ),
    "skip_items": EndpointSpec(
        "skip_items", "POST", "/api/scripted/playout/build/{buildId}/skip_items", ControlSkipItems, None
    ),
    "skip_to_item": EndpointSpec(
        "skip_to_item", "POST", "/api/scripted/playout/build/{buildId}/skip_to_item", ControlSkipToItem, None
    ),
    "wait_until_exact": EndpointSpec(
        "wait_until_exact",
        "POST",
        "/api/scripted/playout/build/{buildId}/wait_until_exact",
        ControlWaitUntilExact,
        PlayoutContext,
    ),
    "wait_until": EndpointSpec(
        "wait_until", "POST", "/api/scripted/playout/build/{buildId}/wait_until", ControlWaitUntil, PlayoutContext
    ),
}


class ErsatzTVScriptedScheduleAPI:
    """Client for driving an ErsatzTV scripted schedule playout build.

    Args:
        host_url: Base URL of the ErsatzTV instance, for example
            ``http://localhost:8409``.
        build_id: UUID of the scripted schedule playout build.
        session: Optional ``requests.Session`` to reuse connections or inject auth.
        timeout: Request timeout in seconds. Pass ``None`` to let requests use
            no timeout.
        headers: Optional headers added to the session, for example API auth.
    """

    def __init__(
        self,
        host_url: str,
        build_id: str,
        *,
        session: Optional[requests.Session] = None,
        timeout: Optional[float] = 30.0,
        headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.host_url = host_url.rstrip("/")
        self.build_id = str(build_id)
        self.timeout = timeout
        self.session = session or requests.Session()
        if headers:
            self.session.headers.update(dict(headers))

    def _build_url(self, path_template: str, **path_params: Any) -> str:
        params = {"buildId": self.build_id, **path_params}
        encoded = {key: quote(str(value), safe="") for key, value in params.items()}
        return f"{self.host_url}{path_template.format(**encoded)}"

    @staticmethod
    def _payload_to_json(payload: Optional[Payload]) -> Optional[Dict[str, Any]]:
        if payload is None:
            return None
        if isinstance(payload, BaseModel):
            return payload.to_dict()
        if isinstance(payload, Mapping):
            return dict(payload)
        raise TypeError(f"Payload must be a BaseModel or mapping, got {type(payload)!r}")

    def _request(
        self,
        method: str,
        path_template: str,
        *,
        payload: Optional[Payload] = None,
        params: QueryParams = None,
        response_model: Optional[Type[BaseModel]] = None,
        **path_params: Any,
    ) -> Any:
        url = self._build_url(path_template, **path_params)
        response = self.session.request(
            method=method,
            url=url,
            json=self._payload_to_json(payload),
            params=params,
            timeout=self.timeout,
        )

        if not 200 <= response.status_code < 300:
            raise ErsatzTVAPIError(
                method=method,
                url=url,
                status_code=response.status_code,
                response_text=response.text,
            )

        if response_model is None:
            return None

        if not response.content:
            return None

        data = response.json()
        return response_model.from_dict(data)

    # ---------- API methods ----------

    def get_context(self, *, params: QueryParams = None) -> PlayoutContext:
        return self._request("GET", ENDPOINTS["get_context"].path, params=params, response_model=PlayoutContext)

    def add_collection(self, payload: Union[ContentCollection, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["add_collection"].path, payload=payload, params=params)

    def add_marathon(self, payload: Union[ContentMarathon, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["add_marathon"].path, payload=payload, params=params)

    def add_multi_collection(
        self, payload: Union[ContentMultiCollection, Mapping[str, Any]], *, params: QueryParams = None
    ) -> None:
        return self._request("POST", ENDPOINTS["add_multi_collection"].path, payload=payload, params=params)

    def add_playlist(self, payload: Union[ContentPlaylist, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["add_playlist"].path, payload=payload, params=params)

    def create_playlist(
        self, payload: Union[ContentCreatePlaylist, Mapping[str, Any]], *, params: QueryParams = None
    ) -> None:
        return self._request("POST", ENDPOINTS["create_playlist"].path, payload=payload, params=params)

    def add_search(self, payload: Union[ContentSearch, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["add_search"].path, payload=payload, params=params)

    def add_smart_collection(
        self, payload: Union[ContentSmartCollection, Mapping[str, Any]], *, params: QueryParams = None
    ) -> None:
        return self._request("POST", ENDPOINTS["add_smart_collection"].path, payload=payload, params=params)

    def add_show(self, payload: Union[ContentShow, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["add_show"].path, payload=payload, params=params)

    def add_all(self, payload: Union[ContentAll, Mapping[str, Any]], *, params: QueryParams = None) -> PlayoutContext:
        return self._request("POST", ENDPOINTS["add_all"].path, payload=payload, params=params, response_model=PlayoutContext)

    def add_count(self, payload: Union[PlayoutCount, Mapping[str, Any]], *, params: QueryParams = None) -> PlayoutContext:
        return self._request("POST", ENDPOINTS["add_count"].path, payload=payload, params=params, response_model=PlayoutContext)

    def add_duration(
        self, payload: Union[PlayoutDuration, Mapping[str, Any]], *, params: QueryParams = None
    ) -> PlayoutContext:
        return self._request(
            "POST", ENDPOINTS["add_duration"].path, payload=payload, params=params, response_model=PlayoutContext
        )

    def pad_to_next(
        self, payload: Union[PlayoutPadToNext, Mapping[str, Any]], *, params: QueryParams = None
    ) -> PlayoutContext:
        return self._request(
            "POST", ENDPOINTS["pad_to_next"].path, payload=payload, params=params, response_model=PlayoutContext
        )

    def pad_until(
        self, payload: Union[PlayoutPadUntil, Mapping[str, Any]], *, params: QueryParams = None
    ) -> PlayoutContext:
        return self._request("POST", ENDPOINTS["pad_until"].path, payload=payload, params=params, response_model=PlayoutContext)

    def pad_until_exact(
        self, payload: Union[PlayoutPadUntilExact, Mapping[str, Any]], *, params: QueryParams = None
    ) -> PlayoutContext:
        return self._request(
            "POST", ENDPOINTS["pad_until_exact"].path, payload=payload, params=params, response_model=PlayoutContext
        )

    def peek_next(self, content: str, *, params: QueryParams = None) -> PeekItemDuration:
        return self._request(
            "GET",
            ENDPOINTS["peek_next"].path,
            params=params,
            response_model=PeekItemDuration,
            content=content,
        )

    def start_epg_group(
        self, payload: Optional[Union[ControlStartEpgGroup, Mapping[str, Any]]] = None, *, params: QueryParams = None
    ) -> None:
        return self._request("POST", ENDPOINTS["start_epg_group"].path, payload=payload or {}, params=params)

    def stop_epg_group(self, *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["stop_epg_group"].path, params=params)

    def graphics_on(self, payload: Union[ControlGraphicsOn, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["graphics_on"].path, payload=payload, params=params)

    def graphics_off(
        self, payload: Optional[Union[ControlGraphicsOff, Mapping[str, Any]]] = None, *, params: QueryParams = None
    ) -> None:
        return self._request("POST", ENDPOINTS["graphics_off"].path, payload=payload or {}, params=params)

    def watermark_on(self, payload: Union[ControlWatermarkOn, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["watermark_on"].path, payload=payload, params=params)

    def watermark_off(
        self, payload: Optional[Union[ControlWatermarkOff, Mapping[str, Any]]] = None, *, params: QueryParams = None
    ) -> None:
        return self._request("POST", ENDPOINTS["watermark_off"].path, payload=payload or {}, params=params)

    def pre_roll_on(self, payload: Union[ControlPreRollOn, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["pre_roll_on"].path, payload=payload, params=params)

    def pre_roll_off(self, *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["pre_roll_off"].path, params=params)

    def skip_items(self, payload: Union[ControlSkipItems, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["skip_items"].path, payload=payload, params=params)

    def skip_to_item(self, payload: Union[ControlSkipToItem, Mapping[str, Any]], *, params: QueryParams = None) -> None:
        return self._request("POST", ENDPOINTS["skip_to_item"].path, payload=payload, params=params)

    def wait_until_exact(
        self, payload: Union[ControlWaitUntilExact, Mapping[str, Any]], *, params: QueryParams = None
    ) -> PlayoutContext:
        return self._request(
            "POST", ENDPOINTS["wait_until_exact"].path, payload=payload, params=params, response_model=PlayoutContext
        )

    def wait_until(
        self, payload: Union[ControlWaitUntil, Mapping[str, Any]], *, params: QueryParams = None
    ) -> PlayoutContext:
        return self._request("POST", ENDPOINTS["wait_until"].path, payload=payload, params=params, response_model=PlayoutContext)


# Short alias for consumers that prefer a concise name.
ScriptedScheduleClient = ErsatzTVScriptedScheduleAPI


__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "ErsatzTVAPIError",
    "ErsatzTVScriptedScheduleAPI",
    "ScriptedScheduleClient",
]
