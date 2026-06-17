from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

_StartupChecksSerializer = inline_serializer(
    name="StartupChecks",
    fields={
        "postgres": serializers.CharField(),
        "migrations": serializers.CharField(),
    },
)

StartupResponseSerializer = inline_serializer(
    name="StartupResponse",
    fields={
        "status": serializers.CharField(),
        "checks": _StartupChecksSerializer,
    },
)

StartupDegradedResponseSerializer = inline_serializer(
    name="StartupDegradedResponse",
    fields={
        "status": serializers.CharField(),
        "error": serializers.CharField(),
    },
)
