from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'identity'

    def ready(self) -> None:
        try:
            import identity.infrastructure.auth_integration.spectacular_extensions
        except ImportError:
            pass
