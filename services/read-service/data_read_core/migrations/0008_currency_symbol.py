"""Add the presentation symbol to the currency reference table.

Split from `0007_seed_currencies` rather than folded into it: that migration has
already run everywhere, so the column arrives empty and is backfilled here. A
code with no symbol keeps the empty string and the client falls back to the code
itself.
"""

from django.db import migrations, models

SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CHF": "CHF",
    "CAD": "CA$",
    "AUD": "A$",
    "CNY": "CN¥",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "PLN": "zł",
    "CZK": "Kč",
    "HUF": "Ft",
    "RUB": "₽",
    "INR": "₹",
    "BRL": "R$",
    "MXN": "MX$",
    "ZAR": "R",
    "KRW": "₩",
    "SGD": "S$",
    "HKD": "HK$",
    "NZD": "NZ$",
    "TRY": "₺",
    "AED": "د.إ",
    "SAR": "﷼",
    "THB": "฿",
    "MYR": "RM",
    "IDR": "Rp",
    "PHP": "₱",
    "VND": "₫",
    "UAH": "₴",
    "ILS": "₪",
    "EGP": "E£",
}


def fill_symbols(apps, schema_editor):
    CurrencyReadModel = apps.get_model("data_read_core", "CurrencyReadModel")
    for code, symbol in SYMBOLS.items():
        CurrencyReadModel.objects.filter(code=code).update(symbol=symbol)


def clear_symbols(apps, schema_editor):
    CurrencyReadModel = apps.get_model("data_read_core", "CurrencyReadModel")
    CurrencyReadModel.objects.update(symbol="")


class Migration(migrations.Migration):
    dependencies = [
        ("data_read_core", "0007_seed_currencies"),
    ]

    operations = [
        migrations.AddField(
            model_name="currencyreadmodel",
            name="symbol",
            field=models.CharField(default="", max_length=8),
            preserve_default=False,
        ),
        migrations.RunPython(fill_symbols, clear_symbols),
    ]
