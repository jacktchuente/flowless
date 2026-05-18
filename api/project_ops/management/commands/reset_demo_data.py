from django.core.management.base import BaseCommand

from project_ops.demo import DemoDataResetService


class Command(BaseCommand):
    help = "Remove the demo dataset created for the UI showcase."

    def handle(self, *args, **options):
        DemoDataResetService.run()
        self.stdout.write(self.style.SUCCESS("Demo data removed."))
