from django.apps import AppConfig


class CustomAuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'custom_audit'

    def ready(self):
        from .signals import register_signals
        register_signals()
