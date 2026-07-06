from django.apps import AppConfig


class EditorialPlanningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'editorial_planning'

    def ready(self):
        from editorial_planning.signals import init_signals
        init_signals()
        return super(EditorialPlanningConfig, self).ready()