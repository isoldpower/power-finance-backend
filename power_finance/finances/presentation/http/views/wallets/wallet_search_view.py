import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from finances.domain.exceptions import FilterParseError
from finances.application.use_cases import (
    ListFilteredWalletsQuery,
    ListFilteredWalletsQueryHandler,
)

from .base import WalletView
from ...mixins import IdempotentMixin
from ...serializers import (
    WalletResponseSerializer,
    MessageResponseSerializer,
    FilterWalletsRequestSerializer,
)
from ...presenters import (
    WalletHttpPresenter,
    CommonHttpPresenter,
    MessageResultInfo,
)

logger = logging.getLogger(__name__)


class WalletSearchView(IdempotentMixin, WalletView):
    @extend_schema(
        methods=["POST"],
        operation_id="wallets_search",
        summary="Search wallets with filters",
        description="Retrieve a list of wallets by applying a filter tree passed in the request body.",
        request=FilterWalletsRequestSerializer,
        responses={
            200: WalletResponseSerializer(many=True),
            400: MessageResponseSerializer,
            500: MessageResponseSerializer
        }
    )
    async def post(self, request):
        logger.info("WalletViewSet: Received POST request for filtered wallets search (User ID: %s)", request.user.id)
        serializer = FilterWalletsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            handler = ListFilteredWalletsQueryHandler()
            filtered_wallets = await handler.handle(ListFilteredWalletsQuery(
                user_id=request.user.id,
                filter_body=validated_data.get("filter_body"),
            ))

            paginator = self.pagination_class()
            paginated_response = paginator.paginate_queryset(filtered_wallets, request, view=self)
            payload = WalletHttpPresenter.present_many(paginated_response)

            logger.info("WalletViewSet: Successfully searched filtered wallets for User ID: %s", request.user.id)
            return paginator.get_paginated_response(payload)
        except FilterParseError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Error occurred while resolving the passed filtration tree:\n {e}",
                resource_id=None
            ))

            logger.error("WalletViewSet: Filter parse error for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get filtered wallets with passed filters:\n {e}",
                resource_id=None
            ))

            logger.error("WalletViewSet: Error searching filtered wallets for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)