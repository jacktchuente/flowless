from django.apps import AppConfig


class RuleEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rule_engine'

    def ready(self):
        from rule_engine.signals import init_signals
        init_signals()
        return super(RuleEngineConfig, self).ready()