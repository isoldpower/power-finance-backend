import logging
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.core.exceptions import ObjectDoesNotExist

from finances.application.use_cases import (
    GetWalletBalanceHistoryQueryHandler,
    GetWalletBalanceHistoryQuery,
)

from .base import AnalyticsView
from ...serializers import WalletBalanceHistorySerializer, MessageResponseSerializer
from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter

logger = logging.getLogger(__name__)


class WalletBalanceHistoryView(AnalyticsView):
    @extend_schema(
        operation_id="analytics_wallet_balance_history_retrieve",
        summary="Wallet balance history",
        description="Retrieve historical balance measurements for a specific wallet.",
        parameters=[OpenApiParameter(
            'id',
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Wallet ID"
        )],
        responses={
            200: WalletBalanceHistorySerializer,
            400: MessageResponseSerializer,
            404: serializers.Serializer
        }
    )
    async def get(self, request: Request, pk=None) -> Response:
        try:
            handler = GetWalletBalanceHistoryQueryHandler()
            result = await handler.handle(GetWalletBalanceHistoryQuery(
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

            logger.error("WalletBalanceHistoryView: Error for User ID: %s, Wallet ID: %s - %s", request.user.id, pk, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
