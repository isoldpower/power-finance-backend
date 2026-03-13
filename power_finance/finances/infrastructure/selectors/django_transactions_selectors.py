from uuid import UUID
from django.db.models import Sum, Q, Case, When, DecimalField
from django.db.models.functions import TruncMonth, TruncDate

from finances.application.interfaces import TransactionSelectorsCollection
from finances.domain.entities import TransactionType

from ..orm import TransactionModel


class DjangoTransactionSelectorsCollection(TransactionSelectorsCollection):
    def get_expenses_by_category(self, user_id: int) -> list[dict[str, str]]:
        category_transactions = (TransactionModel.objects
            .filter(
                send_wallet__user_id=user_id,
                type=TransactionType.EXPENSE,
            )
            .values("category")
            .annotate(amount=Sum("send_amount"))
            .order_by("-amount"))

        return list(category_transactions)

    def get_monthly_expenditure_and_income(self, user_id: int) -> list[dict[str, str]]:
        monthly_expenditure_and_income = (TransactionModel.objects
            .filter(
                Q(send_wallet__user_id=user_id) |
                Q(receive_wallet__user_id=user_id)
            )
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(
                income=Sum(Case(
                    When(type=TransactionType.INCOME, then="receive_amount"),
                    default=0,
                    output_field=DecimalField()
                )),
                expenses=Sum(Case(
                    When(type=TransactionType.EXPENSE, then="send_amount"),
                    default=0,
                    output_field=DecimalField()
                )))
            .order_by("month")                              )

        return list(monthly_expenditure_and_income)

    def get_user_transfers_grouped(self, user_id: int) -> list[dict[str, str]]:
        grouped_transactions = (TransactionModel.objects
                                .filter(
            send_wallet__user_id=user_id,
            receive_wallet__user_id=user_id,
            type=TransactionType.TRANSFER,
        )
                                .values("send_wallet__id", "receive_wallet__id")
                                .annotate(total=Sum("send_amount"))
                                )

        return list(grouped_transactions)

    def get_daily_spending(self, user_id: int) -> list[dict[str, any]]:
        daily_spending = (TransactionModel.objects
            .filter(
                send_wallet__user_id=user_id,
                send_wallet__deleted_at__isnull=True,
                type=TransactionType.EXPENSE
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("send_amount"))
            .order_by("day"))

        return list(daily_spending)

    def get_wallet_transactions(self, wallet_id: UUID) -> list[dict[str, any]]:
        wallet_transactions = (TransactionModel.objects
            .filter(Q(send_wallet__id=wallet_id) | Q(receive_wallet__id=wallet_id))
            .order_by("created_at")
            .values(
                "send_wallet_id",
                "receive_wallet_id",
                "send_amount",
                "receive_amount",
                "created_at"
            ))

        return list(wallet_transactions)