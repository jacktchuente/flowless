from __future__ import annotations

from typing import Any

from utils.websocket_service import broadcast_crud_event


def save_status_and_broadcast(instance: Any, *, object_type: str, status: Any) -> None:
    instance.analyze_status = status
    instance.save()
    broadcast_crud_event(object_type=object_type, object_id=instance.id, action="update")


def broadcast_refresh(object_type: str, object_id: int | str = 0) -> None:
    broadcast_crud_event(object_type=object_type, object_id=object_id, action="update")
