from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

_ReadinessChecksSerializer = inline_serializer(
    name="ReadinessChecks", fields={"postgres": serializers.CharField()}
)

ReadinessResponseSerializer = inline_serializer(
    name="ReadinessResponse",
    fields={
        "status": serializers.CharField(),
        "checks": _ReadinessChecksSerializer,
    },
)
ReadinessDegradedResponseSerializer = inline_serializer(
    name="ReadinessDegradedResponse",
    fields={
        "status": serializers.CharField(),
        "error": serializers.CharField(),
    },
)
