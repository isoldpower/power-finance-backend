from rest_framework import serializers

from data_read_core.shared.rest_framework import automation_fields, resource_response


class AutomationDetailSerializer(serializers.Serializer):
    pass


AutomationDetailSerializer._declared_fields.update(automation_fields())

EnvelopedAutomationDetailSerializer = resource_response(AutomationDetailSerializer)
