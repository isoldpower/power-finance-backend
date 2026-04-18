from django.core.management import BaseCommand

from finances.infrastructure.orm import WalletModel


class Command(BaseCommand):
    help = "Erase seeded wallets (transactions are stored in immudb)"

    def handle(self, *args, **options):
        self.stdout.write("Erasing Wallet model objects...")
        wallets = WalletModel.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f"Erased {wallets[0]} wallets. Erase immudb transactions separately."
        ))
