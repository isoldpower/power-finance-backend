from datetime import UTC, datetime
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from data_write_core.domain.value_objects import CategoryKind, global_category_id

APP = "data_write_core"
BEFORE_CATEGORIES = [(APP, "0016_outbox_propagation_context")]
AFTER_CATEGORIES = [(APP, "0019_category_columns_swap")]
NOW = datetime(2026, 11, 1, tzinfo=UTC)


class CategoryMigrationTests(TransactionTestCase):
    def setUp(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(BEFORE_CATEGORIES)
        self.old_apps = executor.loader.project_state(BEFORE_CATEGORIES).apps

    def tearDown(self) -> None:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes(APP))

    def _migrate_forward(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(AFTER_CATEGORIES)
        return executor.loader.project_state(AFTER_CATEGORIES).apps

    def test_free_text_categories_are_matched_to_globals_or_cleared(self) -> None:
        user = self.old_apps.get_model("auth", "User").objects.create(username="migrated-owner")
        self.old_apps.get_model(APP, "CurrencyModel").objects.get_or_create(
            code="USD",
            defaults={"name": "US Dollar", "numeric": "840", "digits": 2},
        )
        wallet_model = self.old_apps.get_model(APP, "WalletModel")
        matched_wallet = wallet_model.objects.create(
            kind="wallet", name="Main", currency_id="USD", user=user, category="banking"
        )
        unmatched_wallet = wallet_model.objects.create(
            kind="wallet", name="Odd", currency_id="USD", user=user, category="WWWWW"
        )
        transaction_model = self.old_apps.get_model(APP, "TransactionModel")
        matched_transaction = transaction_model.objects.create(
            id=uuid4(),
            user=user,
            container_id=matched_wallet.pk,
            name="Lunch",
            category="FOOD",
            created_at=NOW,
        )
        unmatched_transaction = transaction_model.objects.create(
            id=uuid4(),
            user=user,
            container_id=matched_wallet.pk,
            name="Mystery",
            category="Wasd",
            created_at=NOW,
        )
        automation_model = self.old_apps.get_model(APP, "AutomationModel")
        matched_rule = automation_model.objects.create(
            user=user,
            name="Tag lunch",
            trigger_type="event",
            effects=[{"type": "set_category", "params": {"category": "dining"}}],
        )
        unmatched_rule = automation_model.objects.create(
            user=user,
            name="Tag mystery",
            trigger_type="event",
            effects=[{"type": "set_category", "params": {"category": "Mystery"}}],
        )

        new_apps = self._migrate_forward()

        new_wallet_model = new_apps.get_model(APP, "WalletModel")
        new_transaction_model = new_apps.get_model(APP, "TransactionModel")
        self.assertEqual(
            new_wallet_model.objects.get(pk=matched_wallet.pk).category_id,
            global_category_id(CategoryKind.WALLET, "Banking"),
        )
        self.assertIsNone(new_wallet_model.objects.get(pk=unmatched_wallet.pk).category_id)
        self.assertEqual(
            new_transaction_model.objects.get(pk=matched_transaction.pk).category_id,
            global_category_id(CategoryKind.TRANSACTION, "Food"),
        )
        self.assertIsNone(
            new_transaction_model.objects.get(pk=unmatched_transaction.pk).category_id
        )

        new_automation_model = new_apps.get_model(APP, "AutomationModel")
        self.assertEqual(
            new_automation_model.objects.get(pk=matched_rule.pk).effects,
            [
                {
                    "type": "set_category",
                    "params": {
                        "category_id": str(global_category_id(CategoryKind.TRANSACTION, "Dining"))
                    },
                }
            ],
        )
        emptied_rule = new_automation_model.objects.get(pk=unmatched_rule.pk)
        self.assertEqual(emptied_rule.effects, [])
        self.assertFalse(emptied_rule.enabled)
