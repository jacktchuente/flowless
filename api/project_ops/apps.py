from django.apps import AppConfig


class ProjectOpsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project_ops'

    def ready(self):
        from project_ops.signals import init_signals
        init_signals()
        return super(ProjectOpsConfig, self).ready()