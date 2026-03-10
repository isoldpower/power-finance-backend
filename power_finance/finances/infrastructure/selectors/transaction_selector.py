from django.db.models import Sum

from ..orm.transaction import TransactionModel, TransactionTypeChoices


class TransactionSelector:
    def get_grouped_internal_transfers(self, user_id):
        return list(
            TransactionModel.objects
            .filter(
                from_wallet__user_id=user_id,
                to_wallet__user_id=user_id,
                type=TransactionTypeChoices.TRANSFER.value,
            )
            .values("send_wallet_id", "receive_wallet_id")
            .annotate(total=Sum("send_amount"))
        )