from uuid import UUID

from django.db.models import Q, QuerySet
from write_service.common.pagination import PageRequest, apply_keyset

from data_write_core.application.interfaces import CategoryRepository
from data_write_core.domain.entities import CategoryEntity
from data_write_core.domain.exceptions import CategoryNotFoundError
from data_write_core.domain.value_objects import CategoryKind

from ..orm import CategoryModel, TransactionCategoryModel, WalletCategoryModel
from .mappers import CategoryMapper

SUBTYPE_MODEL_BY_KIND: dict[CategoryKind, type[CategoryModel]] = {
    CategoryKind.TRANSACTION: TransactionCategoryModel,
    CategoryKind.WALLET: WalletCategoryModel,
}


class DjangoCategoryRepository(CategoryRepository):
    async def get_visible_category(self, category_id: UUID, user_id: int) -> CategoryEntity:
        category_row = await (
            CategoryModel.objects.with_deleted()
            .filter(_visible_to(user_id), id=category_id)
            .afirst()
        )
        if category_row is None:
            raise CategoryNotFoundError(category_id)

        return CategoryMapper.to_domain(category_row)

    async def get_visible_categories(
        self,
        user_id: int,
        kind: CategoryKind | None = None,
        page: PageRequest | None = None,
    ) -> list[CategoryEntity]:
        queryset = _live_visible(user_id, kind)
        rows = (
            apply_keyset(queryset, page) if page else queryset.order_by("-is_global", "name", "id")
        )

        return [CategoryMapper.to_domain(row) async for row in rows]

    async def count_visible_categories(self, user_id: int, kind: CategoryKind | None = None) -> int:
        return await _live_visible(user_id, kind).acount()

    async def is_name_taken(
        self,
        user_id: int,
        kind: CategoryKind,
        name: str,
        excluding_category_id: UUID | None = None,
    ) -> bool:
        clashing = _live_visible(user_id, kind).filter(name__iexact=name)
        if excluding_category_id is not None:
            clashing = clashing.exclude(id=excluding_category_id)

        return await clashing.aexists()

    async def create_category(self, category: CategoryEntity) -> CategoryEntity:
        created_category = SUBTYPE_MODEL_BY_KIND[category.kind]()
        CategoryMapper.apply_to_model(created_category, category)
        await created_category.asave()

        return CategoryMapper.to_domain(created_category)

    async def save_category(self, category: CategoryEntity) -> CategoryEntity:
        stored_category = await CategoryModel.objects.with_deleted().aget(id=category.unique_id)
        CategoryMapper.apply_to_model(stored_category, category)
        await stored_category.asave()

        return category

    async def hard_delete_category(self, category_id: UUID) -> None:
        await CategoryModel.objects.with_deleted().filter(id=category_id).adelete()


def _visible_to(user_id: int) -> Q:
    return Q(is_global=True) | Q(user_id=user_id)


def _live_visible(user_id: int, kind: CategoryKind | None) -> QuerySet[CategoryModel]:
    queryset = CategoryModel.objects.filter(_visible_to(user_id))
    if kind is not None:
        queryset = queryset.filter(kind=str(kind))

    return queryset
