from django.apps import AppConfig


class IptvPlayerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'iptv_player'

    def ready(self):
        from iptv_player.signals import init_signals
        init_signals()
        return super(IptvPlayerConfig, self).ready()