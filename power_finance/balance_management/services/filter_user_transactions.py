from ..models import Transaction, Wallet
from django.db import models


def get_transactions_of_user(request):
    user_wallets = Wallet.objects.filter(user=request.user)

    return Transaction.objects.select_related(
        'from_wallet__currency',
        'to_wallet__currency',
    ).filter(
        models.Q(from_wallet__in=user_wallets) | models.Q(to_wallet__in=user_wallets)
    )