from drf_spectacular.utils import extend_schema
from write_service.common.http_contract import ok
from write_service.common.pagination import CATEGORY_LISTING, PageRequest, build_page

from data_write_core.application.queries import (
    ListFallbackCategoriesQuery,
    ListFallbackCategoriesQueryHandler,
)
from data_write_core.domain.value_objects import CategoryKind

from ...decorators import trace_handler_flow
from ...presenters import CategoryHttpPresenter
from ...serializers import ErrorResponseSerializer, PaginatedCategoryResponseSerializer
from ._query_params import resolve_choice
from .base import FallbackReadView
from .config import CATEGORY_KIND_PARAMETER, CURSOR_PARAMETER, LIMIT_PARAMETER


class FallbackCategoryListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_categories_list",
        summary="List categories (consistent fallback)",
        description=(
            "Always-consistent category list served from the write side: the global "
            "categories followed by the user's own, alphabetically. The gateway "
            "routes here when the Read Service is not caught up."
        ),
        parameters=[CATEGORY_KIND_PARAMETER, LIMIT_PARAMETER, CURSOR_PARAMETER],
        responses={
            200: PaginatedCategoryResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        requested_kind = resolve_choice(request, "kind", CategoryKind)
        page_request = PageRequest.from_request(request, CATEGORY_LISTING)
        categories, total = await ListFallbackCategoriesQueryHandler().handle(
            ListFallbackCategoriesQuery(
                user_id=int(request.user.unique_id),
                page=page_request,
                kind=CategoryKind(requested_kind) if requested_kind else None,
            )
        )

        page = build_page(categories, total, page_request)
        return ok(
            CategoryHttpPresenter.present_many(page.items),
            page.meta(cached=False),
        )
