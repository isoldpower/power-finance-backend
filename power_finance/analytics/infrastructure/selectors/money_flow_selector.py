from django.db.models import Sum

from finances.models import Transaction, TransactionType


class MoneyFlowSelector:
    def get_user_transfers_grouped(self, user_id: str) -> list[dict[str, str]]:
        return list(
            Transaction.objects
            .filter(
                from_wallet__user_id=user_id,
                to_wallet__user_id=user_id,
                type=TransactionType.TRANSFER,
            )
            .values("from_wallet__id", "to_wallet__id")
            .annotate(total=Sum("from_amount"))
        )