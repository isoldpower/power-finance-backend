from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Case, When, DecimalField, Q
from django.db.models.functions import TruncMonth

from balance_management.models import Transaction


class ExpenditureAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = (
            Transaction.objects
            .filter(
                Q(from_wallet__user=request.user) |
                Q(to_wallet__user=request.user)
            )
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(
                income=Sum(
                    Case(
                        When(type="income", then="to_amount"),
                        default=0,
                        output_field=DecimalField()
                    )
                ),
                expenses=Sum(
                    Case(
                        When(type="expense", then="from_amount"),
                        default=0,
                        output_field=DecimalField()
                    )
                )
            )
            .order_by("month")
        )

        data = {
            item["month"].isoformat(): {
                "income": float(item["income"] or 0),
                "expenses": float(item["expenses"] or 0)
            }
            for item in transactions
        }

        return Response(data)