from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Sum

from finances.models import Wallet, Transaction, TransactionType


class MoneyFlowAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallets = list(Wallet.objects.filter(user=request.user))

        if not wallets:
            return Response({"nodes": [], "links": []})

        nodes = [
            {
                "name": wallet.name,
                "level": i
            }
            for i, wallet in enumerate(wallets)
        ]

        wallet_index = {
            wallet.id: i
            for i, wallet in enumerate(wallets)
        }

        transfers = (
            Transaction.objects
            .filter(
                from_wallet__user=request.user,
                to_wallet__user=request.user,
                type=TransactionType.TRANSFER
            )
            .values("from_wallet_id", "to_wallet_id")
            .annotate(total=Sum("from_amount"))
        )

        links = []
        seen = set()

        for tx in transfers:
            src = wallet_index.get(tx["from_wallet_id"])
            dst = wallet_index.get(tx["to_wallet_id"])

            if src is None or dst is None:
                continue

            if src == dst:
                continue

            if dst <= src:
                continue

            pair = (src, dst)
            if pair in seen:
                continue

            seen.add(pair)

            value = float(tx["total"] or 0)
            if value <= 0:
                continue

            links.append({
                "source": src,
                "target": dst,
                "value": value
            })

        return Response({
            "nodes": nodes,
            "links": links
        })