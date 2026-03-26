from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter

from finances.application.use_cases import (
    GetWalletBalanceHistoryQueryHandler,
    GetWalletBalanceHistoryQuery,
)


class WalletBalanceHistoryView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.query_handler = GetWalletBalanceHistoryQueryHandler()

    def retrieve(self, request: Request, pk=None) -> Response:
        try:
            result = self.query_handler.handle(GetWalletBalanceHistoryQuery(
                user_id=request.user.id,
                wallet_id=pk
            ))

            data = AnalyticsHttpPresenter.present_wallet_balance_history(result)
            payload = AnalyticsHttpPresenter.present_analytics_data(
                data=data,
                metadata={
                    "history_count": len(result.history)
                }
            )

            return Response(payload, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get wallet balance history: {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
