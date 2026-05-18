"""Typed input/output objects for the ErsatzTV scripted schedule API.

The field names intentionally match the OpenAPI JSON payload names
(e.g. ``customTitle`` and ``disableWatermarks``) so ``to_dict()`` produces
payloads that can be sent directly to the API.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Dict, List, Mapping, Optional, Type, TypeVar, Union, get_args, get_origin, get_type_hints

JsonDict = Dict[str, Any]
T = TypeVar("T", bound="BaseModel")


def _is_base_model_type(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, BaseModel)


def _unwrap_optional(tp: Any) -> Any:
    origin = get_origin(tp)
    if origin is Union:
        args = tuple(arg for arg in get_args(tp) if arg is not type(None))  # noqa: E721
        if len(args) == 1:
            return args[0]
    return tp


def _coerce_value(value: Any, annotation: Any) -> Any:
    """Best-effort conversion from dict/list JSON data into dataclasses."""
    if value is None:
        return None

    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (list, List):
        item_type = args[0] if args else Any
        return [_coerce_value(item, item_type) for item in value]

    if origin in (dict, Dict, Mapping):
        value_type = args[1] if len(args) >= 2 else Any
        return {key: _coerce_value(item, value_type) for key, item in value.items()}

    if _is_base_model_type(annotation) and isinstance(value, Mapping):
        return annotation.from_dict(value)

    return value


def _to_json_value(value: Any, *, omit_none: bool = True) -> Any:
    if value is None:
        return None

    if is_dataclass(value):
        result: JsonDict = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if omit_none and field_value is None:
                continue
            result[field.name] = _to_json_value(field_value, omit_none=omit_none)
        return result

    if isinstance(value, Mapping):
        return {
            key: _to_json_value(item, omit_none=omit_none)
            for key, item in value.items()
            if not (omit_none and item is None)
        }

    if isinstance(value, (list, tuple)):
        return [_to_json_value(item, omit_none=omit_none) for item in value]

    return value


class BaseModel:
    """Base class for all request and response models."""

    def to_dict(self, *, omit_none: bool = True) -> JsonDict:
        """Return a JSON-serializable dictionary.

        Args:
            omit_none: When true, omit fields whose value is ``None``. Set this
                to false when you need to explicitly send JSON ``null``.
        """
        return _to_json_value(self, omit_none=omit_none)

    @classmethod
    def from_dict(cls: Type[T], data: Mapping[str, Any]) -> T:
        """Create a model instance from a JSON dictionary."""
        if data is None:
            raise ValueError(f"Cannot build {cls.__name__} from None")
        if not isinstance(data, Mapping):
            raise TypeError(f"Expected mapping for {cls.__name__}, got {type(data)!r}")

        hints = get_type_hints(cls)
        kwargs: JsonDict = {}
        for field in fields(cls):
            if field.name in data:
                kwargs[field.name] = _coerce_value(data[field.name], hints.get(field.name, Any))
        return cls(**kwargs)  # type: ignore[arg-type]


# ---------- Content payloads ----------


@dataclass
class ContentAll(BaseModel):
    """Payload for AddAll."""

    content: str
    fillerKind: Optional[str] = None
    customTitle: Optional[str] = None
    disableWatermarks: bool = False


@dataclass
class ContentCollection(BaseModel):
    """Payload for AddCollection."""

    key: str
    collection: str
    order: Optional[str] = None


@dataclass
class PlaylistItem(BaseModel):
    """Item used by ContentCreatePlaylist."""

    content: str
    count: int


@dataclass
class ContentCreatePlaylist(BaseModel):
    """Payload for CreatePlaylist."""

    key: str
    items: List[PlaylistItem]


@dataclass
class ContentMarathon(BaseModel):
    """Payload for AddMarathon."""

    key: str
    groupBy: str
    itemOrder: Optional[str] = None
    guids: Optional[Dict[str, List[str]]] = None
    searches: Optional[List[str]] = None
    playAllItems: Optional[bool] = None
    shuffleGroups: Optional[bool] = None


@dataclass
class ContentMultiCollection(BaseModel):
    """Payload for AddMultiCollection."""

    key: str
    multiCollection: str
    order: Optional[str] = None


@dataclass
class ContentPlaylist(BaseModel):
    """Payload for AddPlaylist."""

    key: str
    playlist: str
    playlistGroup: str


@dataclass
class ContentSearch(BaseModel):
    """Payload for AddSearch."""

    key: str
    query: str
    order: Optional[str] = None


@dataclass
class ContentShow(BaseModel):
    """Payload for AddShow."""

    key: str
    guids: Dict[str, str]
    order: Optional[str] = None


@dataclass
class ContentSmartCollection(BaseModel):
    """Payload for AddSmartCollection."""

    key: str
    smartCollection: str
    order: Optional[str] = None


# ---------- Control payloads ----------


@dataclass
class ControlGraphicsOff(BaseModel):
    """Payload for GraphicsOff."""

    graphics: Optional[List[str]] = None


@dataclass
class ControlGraphicsOn(BaseModel):
    """Payload for GraphicsOn."""

    graphics: List[str]
    variables: Optional[Dict[str, str]] = None


@dataclass
class ControlPreRollOn(BaseModel):
    """Payload for PreRollOn."""

    playlist: str


@dataclass
class ControlSkipItems(BaseModel):
    """Payload for SkipItems."""

    content: str
    count: int


@dataclass
class ControlSkipToItem(BaseModel):
    """Payload for SkipToItem."""

    content: str
    season: int
    episode: int


@dataclass
class ControlStartEpgGroup(BaseModel):
    """Payload for StartEpgGroup."""

    advance: Optional[bool] = None
    customTitle: Optional[str] = None


@dataclass
class ControlWaitUntil(BaseModel):
    """Payload for WaitUntil."""

    when: str
    tomorrow: Optional[bool] = None
    rewindOnReset: Optional[bool] = None


@dataclass
class ControlWaitUntilExact(BaseModel):
    """Payload for WaitUntilExact."""

    when: str
    rewindOnReset: Optional[bool] = None


@dataclass
class ControlWatermarkOff(BaseModel):
    """Payload for WatermarkOff."""

    watermark: Optional[List[str]] = None


@dataclass
class ControlWatermarkOn(BaseModel):
    """Payload for WatermarkOn."""

    watermark: List[str]


# ---------- Playout payloads ----------


@dataclass
class PlayoutCount(BaseModel):
    """Payload for AddCount."""

    content: str
    count: int
    fillerKind: Optional[str] = None
    customTitle: Optional[str] = None
    disableWatermarks: bool = False


@dataclass
class PlayoutDuration(BaseModel):
    """Payload for AddDuration."""

    content: str
    duration: str
    fallback: Optional[str] = None
    trim: Optional[bool] = None
    discardAttempts: Optional[int] = None
    stopBeforeEnd: Optional[bool] = None
    offlineTail: Optional[bool] = None
    fillerKind: Optional[str] = None
    customTitle: Optional[str] = None
    disableWatermarks: bool = False


@dataclass
class PlayoutPadToNext(BaseModel):
    """Payload for PadToNext."""

    content: str
    minutes: int
    fallback: Optional[str] = None
    trim: Optional[bool] = None
    discardAttempts: Optional[int] = None
    stopBeforeEnd: Optional[bool] = None
    offlineTail: Optional[bool] = None
    fillerKind: Optional[str] = None
    customTitle: Optional[str] = None
    disableWatermarks: bool = False


@dataclass
class PlayoutPadUntil(BaseModel):
    """Payload for PadUntil."""

    content: str
    when: str
    tomorrow: Optional[bool] = None
    fallback: Optional[str] = None
    trim: Optional[bool] = None
    discardAttempts: Optional[int] = None
    stopBeforeEnd: Optional[bool] = None
    offlineTail: Optional[bool] = None
    fillerKind: Optional[str] = None
    customTitle: Optional[str] = None
    disableWatermarks: bool = False


@dataclass
class PlayoutPadUntilExact(BaseModel):
    """Payload for PadUntilExact."""

    content: str
    when: str
    fallback: Optional[str] = None
    trim: Optional[bool] = None
    discardAttempts: Optional[int] = None
    stopBeforeEnd: Optional[bool] = None
    offlineTail: Optional[bool] = None
    fillerKind: Optional[str] = None
    customTitle: Optional[str] = None
    disableWatermarks: bool = False


# ---------- Output models ----------


@dataclass
class PeekItemDuration(BaseModel):
    """Response body for PeekNext."""

    content: str
    milliseconds: int


@dataclass
class PlayoutContext(BaseModel):
    """Response body returned by endpoints that advance or inspect playout state."""

    currentTime: str
    startTime: str
    finishTime: str
    isDone: bool


__all__ = [
    "BaseModel",
    "JsonDict",
    "ContentAll",
    "ContentCollection",
    "ContentCreatePlaylist",
    "ContentMarathon",
    "ContentMultiCollection",
    "ContentPlaylist",
    "ContentSearch",
    "ContentShow",
    "ContentSmartCollection",
    "ControlGraphicsOff",
    "ControlGraphicsOn",
    "ControlPreRollOn",
    "ControlSkipItems",
    "ControlSkipToItem",
    "ControlStartEpgGroup",
    "ControlWaitUntil",
    "ControlWaitUntilExact",
    "ControlWatermarkOff",
    "ControlWatermarkOn",
    "PeekItemDuration",
    "PlaylistItem",
    "PlayoutContext",
    "PlayoutCount",
    "PlayoutDuration",
    "PlayoutPadToNext",
    "PlayoutPadUntil",
    "PlayoutPadUntilExact",
]
