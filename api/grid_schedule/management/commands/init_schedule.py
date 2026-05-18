from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError

from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from tv_channel.models import TvChannel


class Command(BaseCommand):
    help = "Génère le TvPlayout actif pour une chaîne sur les n jours à venir."

    def add_arguments(self, parser):
        parser.add_argument(
            "channel_id",
            type=int,
            help="ID de la chaîne TV à générer.",
        )
        parser.add_argument(
            "days",
            type=int,
            help="Nombre de jours à générer à partir de maintenant.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Désactive le playout actif existant et en crée un nouveau.",
        )

    def handle(self, *args, **options):
        channel_id = options["channel_id"]
        days = options["days"]
        reset = options["reset"]

        try:
            tv_channel = TvChannel.objects.get(pk=channel_id)
        except TvChannel.DoesNotExist as exc:
            raise CommandError(f"TvChannel with id={channel_id} does not exist.") from exc

        service = TvPlayoutGenerationService(
            tv_channel=tv_channel,
            days=days,
            reset=reset,
        )

        try:
            result = service.generate()
        except ValidationError as exc:
            if hasattr(exc, "messages"):
                raise CommandError(" ; ".join(exc.messages)) from exc
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f"Unexpected error while generating playout: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("TvPlayout generated successfully."))
        self.stdout.write(f"Channel: {tv_channel.name} (id={tv_channel.id})")
        self.stdout.write(f"Playout id: {result.tv_playout.id}")
        self.stdout.write(f"Created new playout: {result.created}")
        self.stdout.write(f"Generated items: {result.generated_items}")

        if result.warnings:
            self.stdout.write(self.style.WARNING("Warnings:"))
            for warning in result.warnings:
                self.stdout.write(f"- {warning}")
