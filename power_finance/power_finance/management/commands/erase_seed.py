from django.core.management import BaseCommand

from finances.infrastructure.orm.wallet import WalletModel
from finances.infrastructure.orm.transaction import TransactionModel


class Command(BaseCommand):
    help = "Seed database with wallets and transactions"

    def handle(self, *args, **options):
        self.stdout.write(f"Erasing Transaction model objects...")
        transactions = TransactionModel.objects.all().delete()
        self.stdout.write(f"Erasing Wallet model objects...")
        wallets = WalletModel.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Erased {wallets[0]} wallets and {transactions[0]} transactions"
            )
        )
