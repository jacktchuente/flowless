from django.core.management.base import BaseCommand

from project_ops.services.init_built_in_data import Initializer


class Command(BaseCommand):
    help = "Initialise les donnees built-in du projet."

    def handle(self, *args, **options):
        Initializer.init_categories()
        Initializer.init_grid_layout_presets()
        self.stdout.write(self.style.SUCCESS("Built-in data initialized."))
