from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

LivenessResponseSerializer = inline_serializer(
    name="LivenessResponse",
    fields={
        "status": serializers.CharField(),
    },
)
LivenessDegradedResponseSerializer = inline_serializer(
    name="LivenessDegradedResponse",
    fields={
        "status": serializers.CharField(),
        "error": serializers.CharField(),
    },
)
