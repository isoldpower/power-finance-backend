import uuid
from rest_framework import serializers

class BatchAcknowledgeRequestSerializer(serializers.Serializer):
    batch = serializers.JSONField()

    def validate_batch(self, value):
        if value == "all" or value == ["all"]:
            return "all"
            
        if isinstance(value, list) and len(value) > 0:
            uuids = []
            for v in value:
                try:
                    uuids.append(uuid.UUID(str(v)))
                except ValueError:
                    raise serializers.ValidationError(f"Invalid UUID: {v}")
            return uuids
            
        raise serializers.ValidationError("Batch must be 'all', ['all'], or a non-empty list of UUIDs.")
