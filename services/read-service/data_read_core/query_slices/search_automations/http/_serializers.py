from rest_framework import serializers

from data_read_core.shared.rest_framework import automation_fields, collection_response


class FilterAutomationsRequestSerializer(serializers.Serializer):
    filter_body = serializers.JSONField(allow_null=False, required=True)


class AutomationSearchResultSerializer(serializers.Serializer):
    pass


AutomationSearchResultSerializer._declared_fields.update(automation_fields())

PaginatedAutomationSearchResultSerializer = collection_response(AutomationSearchResultSerializer)
