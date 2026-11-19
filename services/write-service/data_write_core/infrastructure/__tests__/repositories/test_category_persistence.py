from datetime import UTC, datetime
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import TestCase

from data_write_core.domain.entities import CategoryEntity
from data_write_core.domain.exceptions import CategoryNotFoundError
from data_write_core.domain.value_objects import CategoryKind, global_category_id
from data_write_core.infrastructure.orm import CategoryModel, TransactionCategoryModel
from data_write_core.infrastructure.repositories import DjangoCategoryRepository

NOW = datetime(2026, 11, 1, tzinfo=UTC)


class CategoryPersistenceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = User.objects.create_user(username="category-owner")
        cls.stranger = User.objects.create_user(username="category-stranger")

    async def _own(self, name: str, kind: CategoryKind = CategoryKind.TRANSACTION, user=None):
        return await DjangoCategoryRepository().create_category(
            CategoryEntity.create_owned(
                id=uuid4(),
                kind=kind,
                name=name,
                user_id=str((user or self.owner).id),
                created_at=NOW,
            )
        )

    async def test_global_categories_are_seeded_with_deterministic_ids(self) -> None:
        food = await DjangoCategoryRepository().get_visible_category(
            global_category_id(CategoryKind.TRANSACTION, "Food"),
            self.owner.id,
        )

        self.assertTrue(food.is_global)
        self.assertEqual(food.name, "Food")
        self.assertIsNone(food.user_id)

    async def test_a_created_category_lands_in_its_kind_table(self) -> None:
        created = await self._own("Pets")

        self.assertTrue(
            await TransactionCategoryModel.objects.filter(id=created.unique_id).aexists()
        )
        stored = await CategoryModel.objects.aget(id=created.unique_id)
        self.assertEqual(stored.kind, "transaction")

    async def test_another_users_category_is_not_visible(self) -> None:
        theirs = await self._own("Private", user=self.stranger)

        with self.assertRaises(CategoryNotFoundError):
            await DjangoCategoryRepository().get_visible_category(theirs.unique_id, self.owner.id)

    async def test_listing_puts_globals_first_and_hides_deleted_and_foreign_ones(self) -> None:
        await self._own("Alpha")
        retired = await self._own("Retired")
        retired.mark_deleted(NOW)
        await DjangoCategoryRepository().save_category(retired)
        await self._own("Theirs", user=self.stranger)

        listed = await DjangoCategoryRepository().get_visible_categories(
            self.owner.id, CategoryKind.TRANSACTION
        )
        names = [category.name for category in listed]

        self.assertEqual(names[-1], "Alpha")
        self.assertTrue(all(category.is_global for category in listed[:-1]))
        self.assertNotIn("Retired", names)
        self.assertNotIn("Theirs", names)
        self.assertEqual(
            await DjangoCategoryRepository().count_visible_categories(
                self.owner.id, CategoryKind.TRANSACTION
            ),
            len(listed),
        )

    async def test_global_and_own_names_are_taken_case_insensitively(self) -> None:
        await self._own("Pets")
        repository = DjangoCategoryRepository()

        self.assertTrue(
            await repository.is_name_taken(self.owner.id, CategoryKind.TRANSACTION, "food")
        )
        self.assertTrue(
            await repository.is_name_taken(self.owner.id, CategoryKind.TRANSACTION, "PETS")
        )
        self.assertFalse(await repository.is_name_taken(self.owner.id, CategoryKind.WALLET, "pets"))
        self.assertFalse(
            await repository.is_name_taken(self.stranger.id, CategoryKind.TRANSACTION, "pets")
        )
