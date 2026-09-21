from rest_framework import serializers

from data_read_core.shared.rest_framework import automation_fields, collection_response


class AutomationSerializer(serializers.Serializer):
    """One rule as the list returns it: the complete resource, not a preview."""

    pass


AutomationSerializer._declared_fields.update(automation_fields())

PaginatedAutomationSerializer = collection_response(AutomationSerializer)
