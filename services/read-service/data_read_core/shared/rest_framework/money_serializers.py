from rest_framework import serializers


class MoneySerializer(serializers.Serializer):
    amount = serializers.CharField(
        help_text=(
            "Canonical decimal string at the currency's own scale — two "
            "fraction digits for USD, none for JPY. Never a JSON number."
        ),
    )
    currency = serializers.CharField(help_text="ISO-4217 alphabetic code.")
