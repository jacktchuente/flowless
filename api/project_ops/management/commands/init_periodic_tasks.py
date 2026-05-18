from django.core.management.base import BaseCommand

from django_celery_beat.models import IntervalSchedule, PeriodicTask


PERIODIC_TASK_SPECS = (
    {
        "name": "Generate ready TV channel playouts",
        "task": "tv_channel.tasks.generate_ready_tv_channel_playouts",
        "every": 6,
        "period": IntervalSchedule.HOURS,
    },
    {
        "name": "Analyze active media collections",
        "task": "media_source.tasks.analyze_active_media_collections",
        "every": 3,
        "period": IntervalSchedule.HOURS,
    },
)


class Command(BaseCommand):
    help = "Initialise les taches periodiques du projet sans modifier celles qui existent deja."

    def handle(self, *args, **options):
        for spec in PERIODIC_TASK_SPECS:
            interval, _ = IntervalSchedule.objects.get_or_create(
                every=spec["every"],
                period=spec["period"],
            )

            periodic_task, created = PeriodicTask.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "task": spec["task"],
                    "interval": interval,
                    "enabled": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created periodic task: {periodic_task.name}"))
                continue

            self.stdout.write(self.style.SUCCESS(f"Periodic task already exists: {periodic_task.name}"))
