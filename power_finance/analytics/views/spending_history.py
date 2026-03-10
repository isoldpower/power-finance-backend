from django.db.models.functions import TruncDate
from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finances.models import Transaction


class SpendingHeatmapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = (
            Transaction.objects
            .filter(
                from_wallet__user=request.user,
                type="expense"
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("from_amount"))
            .order_by("day")
        )

        data = {
            item["day"].isoformat(): float(item["total"] or 0)
            for item in transactions
        }

        return Response(data)