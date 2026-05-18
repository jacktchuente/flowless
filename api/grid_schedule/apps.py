from django.apps import AppConfig


class GridScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'grid_schedule'

    def ready(self):
        from grid_schedule.signals import init_signals
        init_signals()
        return super(GridScheduleConfig, self).ready()