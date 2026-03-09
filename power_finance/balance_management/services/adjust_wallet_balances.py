from django.db import models

from ..models import Transaction, Wallet


def adjust_wallet_balances(transaction: Transaction):
    if transaction.from_wallet:
        Wallet.objects.filter(id=transaction.from_wallet_id).update(
            balance_amount=models.F("balance_amount") - transaction.from_amount
        )

    if transaction.to_wallet:
        Wallet.objects.filter(id=transaction.to_wallet_id).update(
            balance_amount=models.F("balance_amount") + transaction.to_amount
        )