"""Seed the read side's copy of the ISO-4217 reference table.

Same list, same values as the write side's `0002_seed_currencies`. Currency
metadata is static and user-independent, so both stores own a seeded copy
instead of one projecting to the other over Kafka.
"""

from django.db import migrations

# (code, name, numeric, digits) — minor unit count per ISO 4217.
SEED_CURRENCIES: list[tuple[str, str, str, int]] = [
    ("USD", "US Dollar", "840", 2),
    ("EUR", "Euro", "978", 2),
    ("GBP", "Pound Sterling", "826", 2),
    ("JPY", "Japanese Yen", "392", 0),
    ("CHF", "Swiss Franc", "756", 2),
    ("CAD", "Canadian Dollar", "124", 2),
    ("AUD", "Australian Dollar", "036", 2),
    ("CNY", "Chinese Yuan", "156", 2),
    ("SEK", "Swedish Krona", "752", 2),
    ("NOK", "Norwegian Krone", "578", 2),
    ("DKK", "Danish Krone", "208", 2),
    ("PLN", "Polish Zloty", "985", 2),
    ("CZK", "Czech Koruna", "203", 2),
    ("HUF", "Hungarian Forint", "348", 2),
    ("RUB", "Russian Ruble", "643", 2),
    ("INR", "Indian Rupee", "356", 2),
    ("BRL", "Brazilian Real", "986", 2),
    ("MXN", "Mexican Peso", "484", 2),
    ("ZAR", "South African Rand", "710", 2),
    ("KRW", "South Korean Won", "410", 0),
    ("SGD", "Singapore Dollar", "702", 2),
    ("HKD", "Hong Kong Dollar", "344", 2),
    ("NZD", "New Zealand Dollar", "554", 2),
    ("TRY", "Turkish Lira", "949", 2),
    ("AED", "UAE Dirham", "784", 2),
    ("SAR", "Saudi Riyal", "682", 2),
    ("THB", "Thai Baht", "764", 2),
    ("MYR", "Malaysian Ringgit", "458", 2),
    ("IDR", "Indonesian Rupiah", "360", 2),
    ("PHP", "Philippine Peso", "608", 2),
    ("VND", "Vietnamese Dong", "704", 0),
    ("UAH", "Ukrainian Hryvnia", "980", 2),
    ("ILS", "Israeli Shekel", "376", 2),
    ("EGP", "Egyptian Pound", "818", 2),
]


def seed_currencies(apps, schema_editor):
    CurrencyReadModel = apps.get_model("data_read_core", "CurrencyReadModel")
    CurrencyReadModel.objects.bulk_create(
        [
            CurrencyReadModel(code=code, name=name, numeric=numeric, digits=digits)
            for code, name, numeric, digits in SEED_CURRENCIES
        ],
        ignore_conflicts=True,
    )


def unseed_currencies(apps, schema_editor):
    CurrencyReadModel = apps.get_model("data_read_core", "CurrencyReadModel")
    CurrencyReadModel.objects.filter(code__in=[currency[0] for currency in SEED_CURRENCIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("data_read_core", "0006_currencyreadmodel_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_currencies, unseed_currencies),
    ]
