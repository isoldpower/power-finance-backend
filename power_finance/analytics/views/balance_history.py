from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from finances.models import Wallet, Transaction


class WalletBalanceHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, wallet_id):
        wallet = get_object_or_404(
            Wallet,
            id=wallet_id,
            user=request.user,
            deleted_at__isnull=True
        )

        transactions = (
            Transaction.objects
            .filter(
                Q(from_wallet=wallet) | Q(to_wallet=wallet)
            )
            .order_by("created_at")
        )

        balance = 0
        history = []

        for tx in transactions:
            if tx.from_wallet_id == wallet.id:
                balance -= tx.from_amount or 0

            if tx.to_wallet_id == wallet.id:
                balance += tx.to_amount or 0

            history.append({
                "date": tx.created_at.date().isoformat(),
                "balance": float(balance)
            })

        return Response(history)