from django.apps import AppConfig


class HealthProbesConfig(AppConfig):
    """Kubernetes/Kong liveness and readiness probes for the Write Service.
    Orthogonal to business code — no domain models, no commands."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "health_probes"
    label = "health_probes"
