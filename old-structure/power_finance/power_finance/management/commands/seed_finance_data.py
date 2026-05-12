import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from finances.infrastructure.orm import WalletModel, CurrencyModel

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with wallets (transactions are stored in immudb)"

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=3)
        parser.add_argument("--wallets", type=int, default=5)

    def handle(self, *args, **options):
        users_count = options["users"]
        wallets_per_user = options["wallets"]

        users = list(User.objects.all()[:users_count])
        if not users:
            self.stdout.write(self.style.ERROR("No users found"))
            return

        self.stdout.write("Ensuring currencies exist...")
        currency_codes = ["USD", "EUR", "GBP"]
        currencies = []
        for code in currency_codes:
            obj, _ = CurrencyModel.objects.get_or_create(
                code=code,
                defaults={"name": code, "symbol": code},
            )
            currencies.append(obj)

        self.stdout.write("Creating wallets...")
        wallets = []
        for user in users:
            for i in range(wallets_per_user):
                wallet = WalletModel.objects.create(
                    name=f"{user.username}_wallet_{i}",
                    currency=random.choice(currencies),
                    user=user,
                )
                wallets.append(wallet)

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(wallets)} wallets. Seed transactions via immudb directly."
        ))