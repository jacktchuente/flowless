from django.apps import AppConfig


class MediaSourceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'media_source'

    def ready(self):
        from media_source.signals import init_signals
        init_signals()
        return super(MediaSourceConfig, self).ready()