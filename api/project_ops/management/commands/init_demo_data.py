from django.core.management.base import BaseCommand

from project_ops.demo import DemoDataSeedService


class Command(BaseCommand):
    help = "Initialize a coherent demo dataset for the UI."

    def handle(self, *args, **options):
        DemoDataSeedService.run()
        self.stdout.write(self.style.SUCCESS("Demo data initialized."))
