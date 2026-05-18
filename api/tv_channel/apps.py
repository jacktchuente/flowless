from django.apps import AppConfig


class TvChannelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tv_channel'

    def ready(self):
        from tv_channel.signals import init_signals
        init_signals()
        return super(TvChannelConfig, self).ready()