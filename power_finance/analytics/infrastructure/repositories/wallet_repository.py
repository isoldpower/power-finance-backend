from finances.models import Wallet


class WalletRepository:
    def get_ordered_user_wallets(self, user_id: str) -> list[Wallet]:
        return list(
            Wallet.objects.filter(user_id=user_id)
            .order_by('created_at', 'id')
        )
