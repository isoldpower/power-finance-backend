"""Library-level constants. The actual header name used at runtime is
sourced from `settings.CORRELATION_ID_HEADER` (each service sets it via its
`.env` file); this value is only a fallback when the setting is missing."""

from django.conf import settings

DEFAULT_HEADER_NAME = "X-Correlation-ID"
SETTING_NAME = "CORRELATION_ID_HEADER"


def resolve_header_name() -> str:
    return getattr(settings, SETTING_NAME, DEFAULT_HEADER_NAME)
