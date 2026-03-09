from django.core.management import BaseCommand

from balance_management.models import Wallet, Transaction


class Command(BaseCommand):
    help = "Seed database with wallets and transactions"

    def handle(self, *args, **options):
        self.stdout.write(f"Erasing Transaction model objects...")
        transactions = Transaction.objects.all().delete()
        self.stdout.write(f"Erasing Wallet model objects...")
        wallets = Wallet.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Erased {wallets[0]} wallets and {transactions[0]} transactions"
            )
        )
