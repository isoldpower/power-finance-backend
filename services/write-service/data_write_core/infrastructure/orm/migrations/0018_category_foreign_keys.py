from uuid import UUID, uuid5

import django.db.models.deletion
from django.db import migrations, models

GLOBAL_CATEGORY_NAMESPACE = UUID("7d3f0f0e-2c1b-4c55-9a43-6f1b9c2e8a10")

GLOBAL_TRANSACTION_CATEGORIES = (
    "Income",
    "Food",
    "Groceries",
    "Dining",
    "Housing",
    "Utilities",
    "Transport",
    "Health",
    "Entertainment",
    "Leisure",
    "Shopping",
    "Travel",
    "Education",
    "Subscriptions",
    "Savings",
    "Gifts",
    "Other",
)

GLOBAL_WALLET_CATEGORIES = (
    "Banking",
    "Savings",
    "Cash",
    "Credit",
    "Investments",
    "Travel",
    "Other",
)

TRANSACTION_KIND = "transaction"
WALLET_KIND = "wallet"


def global_category_id(kind: str, name: str) -> UUID:
    return uuid5(GLOBAL_CATEGORY_NAMESPACE, f"{kind}:{name.casefold()}")


def seed_global_categories(apps, schema_editor):
    for model_name, kind, names in (
        ("TransactionCategoryModel", TRANSACTION_KIND, GLOBAL_TRANSACTION_CATEGORIES),
        ("WalletCategoryModel", WALLET_KIND, GLOBAL_WALLET_CATEGORIES),
    ):
        category_model = apps.get_model("data_write_core", model_name)
        for name in names:
            category_model.objects.update_or_create(
                id=global_category_id(kind, name),
                defaults={"kind": kind, "name": name, "is_global": True, "user": None},
            )


def link_matching_categories(apps, schema_editor):
    for model_name, kind, names in (
        ("TransactionModel", TRANSACTION_KIND, GLOBAL_TRANSACTION_CATEGORIES),
        ("WalletModel", WALLET_KIND, GLOBAL_WALLET_CATEGORIES),
    ):
        owner_model = apps.get_model("data_write_core", model_name)
        for name in names:
            owner_model.objects.filter(category__iexact=name).update(
                category_reference_id=global_category_id(kind, name)
            )


def point_set_category_effects_at_categories(apps, schema_editor):
    automation_model = apps.get_model("data_write_core", "AutomationModel")
    global_ids_by_name = {
        name.casefold(): str(global_category_id(TRANSACTION_KIND, name))
        for name in GLOBAL_TRANSACTION_CATEGORIES
    }

    for automation in automation_model.objects.all():
        rewritten_effects = []
        for effect in automation.effects or []:
            if effect.get("type") != "set_category":
                rewritten_effects.append(effect)
                continue

            category_name = str((effect.get("params") or {}).get("category", ""))
            matched_id = global_ids_by_name.get(category_name.casefold())
            if matched_id is not None:
                rewritten_effects.append({**effect, "params": {"category_id": matched_id}})

        if rewritten_effects == automation.effects:
            continue

        automation.effects = rewritten_effects
        if not rewritten_effects:
            automation.enabled = False
        automation.save(update_fields=["effects", "enabled"])


class Migration(migrations.Migration):
    dependencies = [
        ("data_write_core", "0017_categories"),
    ]

    operations = [
        migrations.RunPython(seed_global_categories, migrations.RunPython.noop),
        migrations.AddField(
            model_name="transactionmodel",
            name="category_reference",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions",
                to="data_write_core.transactioncategorymodel",
            ),
        ),
        migrations.AddField(
            model_name="walletmodel",
            name="category_reference",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="wallets",
                to="data_write_core.walletcategorymodel",
            ),
        ),
        migrations.RunPython(link_matching_categories, migrations.RunPython.noop),
        migrations.RunPython(point_set_category_effects_at_categories, migrations.RunPython.noop),
    ]
