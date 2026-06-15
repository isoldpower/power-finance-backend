from rest_framework import serializers


class HealthStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text='Probe status ("ok" or "degraded")')


class HealthChecksResponseSerializer(HealthStatusResponseSerializer):
    checks = serializers.DictField(
        child=serializers.CharField(),
        help_text='Per-dependency status ("ok" or a failure description)',
    )


class HealthDegradedResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text='Always "degraded"')
    error = serializers.CharField(help_text="Failure description")
