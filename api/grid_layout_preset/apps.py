from django.apps import AppConfig


class GridLayoutPresetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'grid_layout_preset'

    def ready(self):
        from grid_layout_preset.signals import init_signals
        init_signals()
        return super(GridLayoutPresetConfig, self).ready()