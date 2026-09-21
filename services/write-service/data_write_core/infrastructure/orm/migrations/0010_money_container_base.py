import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

COPY_CONTAINERS = """
    INSERT INTO finances_money_containers
        (id, kind, name, currency_id, user_id, created_at, updated_at, deleted_at)
    SELECT id, 'wallet', name, currency_id, user_id, created_at, updated_at, deleted_at
    FROM finances_wallets;

    INSERT INTO finances_money_containers
        (id, kind, name, currency_id, user_id, created_at, updated_at, deleted_at)
    SELECT id, 'goal', name, currency_id, user_id, created_at, updated_at, deleted_at
    FROM finances_goals;
"""

ADOPT_CONTAINER_ID = """
    UPDATE finances_transactions
    SET container_id = COALESCE(wallet_id, goal_id);
"""

RESTORE_CONTAINER_ARC = """
    UPDATE finances_transactions AS txn
    SET wallet_id = CASE WHEN container.kind = 'wallet' THEN txn.container_id END,
        goal_id = CASE WHEN container.kind = 'goal' THEN txn.container_id END
    FROM finances_money_containers AS container
    WHERE container.id = txn.container_id;
    SET CONSTRAINTS ALL IMMEDIATE;
"""

SHARED_COLUMNS = ("name", "currency_id", "user_id", "created_at", "updated_at", "deleted_at")


def _demote_child(table: str, constraint: str) -> str:
    dropped = ", ".join(f"DROP COLUMN {column}" for column in SHARED_COLUMNS)

    return f"""
        ALTER TABLE {table} {dropped};
        ALTER TABLE {table}
            ADD CONSTRAINT {constraint}
            FOREIGN KEY (id) REFERENCES finances_money_containers (id)
            DEFERRABLE INITIALLY DEFERRED;
    """


def _promote_child(table: str, constraint: str) -> str:
    """Undo `_demote_child`: give the table its own copy of the shared columns back
    and refill them from the parent row before the parent table goes away."""
    return f"""
        ALTER TABLE {table} DROP CONSTRAINT {constraint};
        ALTER TABLE {table}
            ADD COLUMN name varchar(120),
            ADD COLUMN currency_id varchar(3)
                REFERENCES finances_currencies (code) DEFERRABLE INITIALLY DEFERRED,
            ADD COLUMN user_id integer
                REFERENCES auth_user (id) DEFERRABLE INITIALLY DEFERRED,
            ADD COLUMN created_at timestamptz,
            ADD COLUMN updated_at timestamptz,
            ADD COLUMN deleted_at timestamptz;
        UPDATE {table} AS child
        SET name = parent.name,
            currency_id = parent.currency_id,
            user_id = parent.user_id,
            created_at = parent.created_at,
            updated_at = parent.updated_at,
            deleted_at = parent.deleted_at
        FROM finances_money_containers AS parent
        WHERE parent.id = child.id;
        -- The foreign keys added above are deferred, so their trigger events are
        -- still pending and Postgres refuses to alter the table until they clear.
        SET CONSTRAINTS ALL IMMEDIATE;
        ALTER TABLE {table}
            ALTER COLUMN name SET NOT NULL,
            ALTER COLUMN currency_id SET NOT NULL,
            ALTER COLUMN user_id SET NOT NULL,
            ALTER COLUMN created_at SET NOT NULL;
        CREATE INDEX ON {table} (currency_id);
        CREATE INDEX ON {table} (user_id);
    """


class Migration(migrations.Migration):
    dependencies = [
        ("data_write_core", "0009_alter_transactionmodel_wallet_goalmodel_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MoneyContainerModel",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[("wallet", "Wallet"), ("goal", "Goal")],
                        editable=False,
                        max_length=16,
                    ),
                ),
                ("name", models.CharField(max_length=120)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "currency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="data_write_core.currencymodel",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="money_containers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "finances_money_containers",
                "indexes": [
                    models.Index(
                        fields=["user", "-created_at", "-id"], name="fmc_user_keyset_idx"
                    )
                ],
            },
        ),
        migrations.RunSQL(sql=COPY_CONTAINERS, reverse_sql=migrations.RunSQL.noop),
        migrations.RemoveIndex(model_name="goalmodel", name="fg_user_keyset_idx"),
        migrations.RemoveIndex(model_name="transactionmodel", name="ft_wallet_created_idx"),
        migrations.RemoveIndex(model_name="transactionmodel", name="ft_goal_created_idx"),
        migrations.RemoveConstraint(
            model_name="transactionmodel", name="ft_exactly_one_container"
        ),
        migrations.AddField(
            model_name="transactionmodel",
            name="container",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions",
                to="data_write_core.moneycontainermodel",
            ),
        ),
        migrations.RunSQL(sql=ADOPT_CONTAINER_ID, reverse_sql=RESTORE_CONTAINER_ARC),
        migrations.AlterField(
            model_name="transactionmodel",
            name="container",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions",
                to="data_write_core.moneycontainermodel",
            ),
        ),
        migrations.RemoveField(model_name="transactionmodel", name="wallet"),
        migrations.RemoveField(model_name="transactionmodel", name="goal"),
        migrations.AddIndex(
            model_name="transactionmodel",
            index=models.Index(fields=["container", "-created_at"], name="ft_container_created_idx"),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="WalletModel"),
                migrations.CreateModel(
                    name="WalletModel",
                    fields=[
                        (
                            "container",
                            models.OneToOneField(
                                db_column="id",
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                related_name="wallet",
                                serialize=False,
                                to="data_write_core.moneycontainermodel",
                            ),
                        ),
                        ("category", models.CharField(blank=True, default="", max_length=120)),
                        ("color", models.CharField(blank=True, default="", max_length=9)),
                        ("favorite", models.BooleanField(default=False)),
                        (
                            "zero_balance",
                            models.DecimalField(decimal_places=2, default=0, max_digits=20),
                        ),
                    ],
                    options={"db_table": "finances_wallets"},
                    bases=("data_write_core.moneycontainermodel",),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=_demote_child("finances_wallets", "finances_wallets_container_fk"),
                    reverse_sql=_promote_child(
                        "finances_wallets", "finances_wallets_container_fk"
                    ),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="GoalModel"),
                migrations.CreateModel(
                    name="GoalModel",
                    fields=[
                        (
                            "container",
                            models.OneToOneField(
                                db_column="id",
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                related_name="goal",
                                serialize=False,
                                to="data_write_core.moneycontainermodel",
                            ),
                        ),
                        ("target", models.DecimalField(decimal_places=2, max_digits=20)),
                        ("finish_at", models.DateTimeField(blank=True, null=True)),
                        ("url", models.URLField(blank=True, max_length=2048, null=True)),
                    ],
                    options={"db_table": "finances_goals"},
                    bases=("data_write_core.moneycontainermodel",),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=_demote_child("finances_goals", "finances_goals_container_fk"),
                    reverse_sql=_promote_child("finances_goals", "finances_goals_container_fk"),
                ),
            ],
        ),
    ]
