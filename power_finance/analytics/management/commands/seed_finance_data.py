import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from finances.models import Wallet, Transaction, TransactionType, ExpenseCategory, Currency

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with wallets and transactions"

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=3)
        parser.add_argument("--wallets", type=int, default=5)
        parser.add_argument("--transactions", type=int, default=5000)

    def handle(self, *args, **options):
        users_count = options["users"]
        wallets_per_user = options["wallets"]
        transactions_count = options["transactions"]

        users = list(User.objects.all()[:users_count])
        if not users:
            self.stdout.write(self.style.ERROR("No users found"))
            return

        # --- Ensure currencies exist ---
        self.stdout.write("Ensuring currencies exist...")
        currency_codes = ["USD", "EUR", "GBP"]
        currencies = []
        for code in currency_codes:
            obj, _ = Currency.objects.get_or_create(
                code=code,
                defaults={"name": code, "symbol": code},
            )
            currencies.append(obj)

        # --- Create wallets ---
        self.stdout.write("Creating wallets...")
        wallets = []
        for user in users:
            for i in range(wallets_per_user):
                wallet = Wallet.objects.create(
                    name=f"{user.username}_wallet_{i}",
                    balance_amount=Decimal("0"),
                    currency=random.choice(currencies),
                    user=user
                )
                wallets.append(wallet)

        # --- Helper: random datetime in past year ---
        start_date = timezone.now() - timedelta(days=365)
        end_date = timezone.now()

        def random_datetime(start, end):
            """Return a random datetime between start and end (including seconds)."""
            delta = end - start
            int_delta = int(delta.total_seconds())
            random_second = random.randint(0, int_delta)
            return start + timedelta(seconds=random_second)

        # --- Create transactions ---
        self.stdout.write(f"Creating {transactions_count} transactions...")
        categories = list(ExpenseCategory)
        transactions = []

        for _ in range(transactions_count):
            tx_type = random.choice([
                TransactionType.EXPENSE,
                TransactionType.INCOME,
                TransactionType.TRANSFER
            ])
            created_at = random_datetime(start_date, end_date)
            amount = Decimal(random.randint(1, 10000))

            if tx_type == TransactionType.EXPENSE:
                wallet = random.choice(wallets)
                transactions.append(Transaction(
                    from_wallet=wallet,
                    from_amount=amount,
                    type=TransactionType.EXPENSE,
                    category=random.choice(categories),
                    created_at=created_at
                ))

            elif tx_type == TransactionType.INCOME:
                wallet = random.choice(wallets)
                transactions.append(Transaction(
                    to_wallet=wallet,
                    to_amount=amount,
                    type=TransactionType.INCOME,
                    category=random.choice(categories),
                    created_at=created_at
                ))

            else:  # TRANSFER
                from_wallet = random.choice(wallets)
                to_wallet = random.choice(wallets)
                if from_wallet == to_wallet:
                    continue
                transactions.append(Transaction(
                    from_wallet=from_wallet,
                    to_wallet=to_wallet,
                    from_amount=amount,
                    to_amount=amount,
                    type=TransactionType.TRANSFER,
                    category=random.choice(categories),
                    created_at=created_at
                ))

        # Bulk create for efficiency
        Transaction.objects.bulk_create(transactions, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(wallets)} wallets and {len(transactions)} transactions"
            )
        )