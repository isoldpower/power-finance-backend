from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from finances.models import Transaction


class CategoriesAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = (
            Transaction.objects
            .filter(
                Q(from_wallet__user=request.user),
                type="expense"
            )
            .values("category")
            .annotate(amount=Sum("from_amount"))
            .order_by("-amount")
        )

        data = [
            {
                "category": item["category"],
                "amount": float(item["amount"] or 0)
            }
            for item in transactions
        ]

        return Response(data)