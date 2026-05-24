from django.conf import settings

DEFAULT_HEADER_NAME = "X-Correlation-ID"
SETTING_NAME = "CORRELATION_ID_HEADER"


def resolve_header_name() -> str:
    return getattr(settings, SETTING_NAME, DEFAULT_HEADER_NAME)
