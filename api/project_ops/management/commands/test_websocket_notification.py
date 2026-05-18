from __future__ import annotations

from django.core.management.base import BaseCommand

from utils.task_status_service import broadcast_refresh
from utils.websocket_service import broadcast_crud_event


class Command(BaseCommand):
    help = "Send a test websocket message to the public notification channel."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=("crud", "refresh"),
            default="crud",
            help="Message mode to send on notification_public.",
        )
        parser.add_argument(
            "--type",
            dest="object_type",
            default="TvChannel",
            help="Object type used for the CRUD payload.",
        )
        parser.add_argument(
            "--id",
            dest="object_id",
            default="999999",
            help="Object id used for the CRUD payload.",
        )
        parser.add_argument(
            "--action",
            default="update",
            help="Action used for the CRUD payload.",
        )

    def handle(self, *args, **options):
        mode = options["mode"]
        object_type = options["object_type"]
        object_id = options["object_id"]
        action = options["action"]

        if mode == "refresh":
            broadcast_refresh(object_type=object_type, object_id=object_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Refresh message sent to notification_public type={object_type} id={object_id}"
                )
            )
            return

        broadcast_crud_event(
            object_type=object_type,
            object_id=object_id,
            action=action,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"CRUD message sent to notification_public type={object_type} id={object_id} action={action}"
            )
        )
