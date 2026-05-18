from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def broadcast_crud_event(*, object_type: str, object_id: int | str, action: str, room: str = "public") -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning(
            "broadcast_crud_event skipped because channel layer is unavailable object_type=%s object_id=%s action=%s room=%s",
            object_type,
            object_id,
            action,
            room,
        )
        return

    payload = {
        "category": "crud",
        "data": {
            "id": object_id,
            "type": object_type,
            "action": action,
        },
    }
    async_to_sync(channel_layer.group_send)(
        f"notification_{room}",
        {
            "type": "notification",
            "message": payload,
        },
    )

