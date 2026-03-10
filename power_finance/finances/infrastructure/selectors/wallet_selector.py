from ..orm.wallet import WalletModel


class WalletSelector:
    def get_user_wallet_rows(self, user_id):
        return list(
            WalletModel.objects
            .filter(user_id=user_id)
            .order_by("id")
            .values("id", "name")
        )