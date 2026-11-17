from rest_framework import serializers


class CreateCategoryRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=["transaction", "wallet"],
        help_text="Which resource the category labels. It cannot change later.",
    )
    name = serializers.CharField(max_length=120)


class UpdateCategoryRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
