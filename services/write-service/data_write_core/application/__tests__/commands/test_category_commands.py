from datetime import UTC, datetime
from uuid import UUID

import pytest

from data_write_core.application.commands import (
    CreateCategoryCommand,
    CreateCategoryCommandHandler,
    DeleteCategoryCommand,
    DeleteCategoryCommandHandler,
    UpdateCategoryCommand,
    UpdateCategoryCommandHandler,
)
from data_write_core.application.commands._category_resolution import CategoryResolverMixin
from data_write_core.domain.entities import CategoryEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.exceptions import (
    CategoryKindMismatchError,
    CategoryNameTakenError,
    CategoryNotFoundError,
    GlobalCategoryImmutableError,
)
from data_write_core.domain.value_objects import CategoryKind, CategoryReference

pytestmark = pytest.mark.django_db(transaction=True)

USER_ID = 7
OTHER_USER_ID = 8
NOW = datetime(2026, 11, 1, tzinfo=UTC)
GLOBAL_FOOD = UUID("aaaaaaaa-0000-0000-0000-000000000001")
OWN_COFFEE = UUID("aaaaaaaa-0000-0000-0000-000000000002")
OWN_RETIRED = UUID("aaaaaaaa-0000-0000-0000-000000000003")
OWN_SIDE_ACCOUNT = UUID("aaaaaaaa-0000-0000-0000-000000000004")
STRANGERS = UUID("aaaaaaaa-0000-0000-0000-000000000005")


def _category(
    category_id: UUID,
    name: str,
    *,
    kind: CategoryKind = CategoryKind.TRANSACTION,
    user_id: int | None = USER_ID,
    deleted: bool = False,
) -> CategoryEntity:
    return CategoryEntity(
        id=category_id,
        kind=kind,
        name=name,
        user_id=str(user_id) if user_id is not None else None,
        is_global=user_id is None,
        created_at=NOW,
        deleted_at=NOW if deleted else None,
        event_collector=EventCollector(),
    )


class FakeCategoryRepository:
    def __init__(self, categories: list[CategoryEntity]) -> None:
        self.categories = {category.unique_id: category for category in categories}
        self.saved: list[CategoryEntity] = []

    def _visible(self, category: CategoryEntity, user_id: int) -> bool:
        return category.is_global or category.user_id == str(user_id)

    async def get_visible_category(self, category_id, user_id):
        category = self.categories.get(str(category_id))
        if category is None or not self._visible(category, user_id):
            raise CategoryNotFoundError(category_id)
        return category

    async def is_name_taken(self, user_id, kind, name, excluding_category_id=None):
        return any(
            category.kind is kind
            and category.deleted_at is None
            and self._visible(category, user_id)
            and category.name.casefold() == name.casefold()
            and category.unique_id != str(excluding_category_id)
            for category in self.categories.values()
        )

    async def create_category(self, category):
        self.categories[category.unique_id] = category
        return category

    async def save_category(self, category):
        self.saved.append(category)
        return category

    async def hard_delete_category(self, category_id):
        self.categories.pop(str(category_id), None)


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.entries: list = []

    async def get_latest_sequence(self) -> int:
        return 42

    async def append(self, entry) -> int:
        self.entries.append(entry)
        return 42


def _repository() -> FakeCategoryRepository:
    return FakeCategoryRepository(
        [
            _category(GLOBAL_FOOD, "Food", user_id=None),
            _category(OWN_COFFEE, "Coffee"),
            _category(OWN_RETIRED, "Retired", deleted=True),
            _category(OWN_SIDE_ACCOUNT, "Side account", kind=CategoryKind.WALLET),
            _category(STRANGERS, "Strangers", user_id=OTHER_USER_ID),
        ]
    )


async def test_a_new_category_is_stored_and_announced():
    repository = _repository()
    outbox = FakeOutboxRepository()

    created, write_version = await CreateCategoryCommandHandler(repository, outbox).handle(
        CreateCategoryCommand(
            user_id=USER_ID,
            user_external_id="user_abc",
            kind=CategoryKind.TRANSACTION,
            name="  Pets  ",
        )
    )

    assert created.name == "Pets"
    assert created.is_global is False
    assert write_version == 42
    assert str(created.id) in repository.categories
    payload = outbox.entries[0].payload
    assert outbox.entries[0].event_type == "CategoryCreated"
    assert payload["name"] == "Pets"
    assert payload["kind"] == "transaction"


async def test_a_name_used_by_a_global_category_is_taken():
    with pytest.raises(CategoryNameTakenError):
        await CreateCategoryCommandHandler(_repository(), FakeOutboxRepository()).handle(
            CreateCategoryCommand(
                user_id=USER_ID,
                user_external_id="user_abc",
                kind=CategoryKind.TRANSACTION,
                name="food",
            )
        )


async def test_the_same_name_is_free_for_the_other_kind():
    created, _ = await CreateCategoryCommandHandler(_repository(), FakeOutboxRepository()).handle(
        CreateCategoryCommand(
            user_id=USER_ID,
            user_external_id="user_abc",
            kind=CategoryKind.WALLET,
            name="Coffee",
        )
    )

    assert created.kind is CategoryKind.WALLET


async def test_a_deleted_name_can_be_reused():
    created, _ = await CreateCategoryCommandHandler(_repository(), FakeOutboxRepository()).handle(
        CreateCategoryCommand(
            user_id=USER_ID,
            user_external_id="user_abc",
            kind=CategoryKind.TRANSACTION,
            name="Retired",
        )
    )

    assert created.name == "Retired"


async def test_renaming_an_own_category_announces_both_names():
    repository = _repository()
    outbox = FakeOutboxRepository()

    renamed, _ = await UpdateCategoryCommandHandler(repository, outbox).handle(
        UpdateCategoryCommand(
            user_id=USER_ID,
            user_external_id="user_abc",
            category_id=OWN_COFFEE,
            name="Coffee & tea",
        )
    )

    assert renamed.name == "Coffee & tea"
    payload = outbox.entries[0].payload
    assert payload["previous_name"] == "Coffee"
    assert payload["new_name"] == "Coffee & tea"


async def test_a_rename_to_the_same_name_announces_nothing():
    outbox = FakeOutboxRepository()

    _, write_version = await UpdateCategoryCommandHandler(_repository(), outbox).handle(
        UpdateCategoryCommand(
            user_id=USER_ID,
            user_external_id="user_abc",
            category_id=OWN_COFFEE,
            name="Coffee",
        )
    )

    assert write_version == 0
    assert outbox.entries == []


@pytest.mark.parametrize(
    "handler_type", [UpdateCategoryCommandHandler, DeleteCategoryCommandHandler]
)
async def test_global_categories_cannot_change(handler_type):
    handler = handler_type(_repository(), FakeOutboxRepository())
    command = (
        UpdateCategoryCommand(USER_ID, "user_abc", GLOBAL_FOOD, "Meals")
        if handler_type is UpdateCategoryCommandHandler
        else DeleteCategoryCommand(USER_ID, "user_abc", GLOBAL_FOOD)
    )

    with pytest.raises(GlobalCategoryImmutableError):
        await handler.handle(command)


async def test_another_users_category_is_not_found():
    with pytest.raises(CategoryNotFoundError):
        await DeleteCategoryCommandHandler(_repository(), FakeOutboxRepository()).handle(
            DeleteCategoryCommand(USER_ID, "user_abc", STRANGERS)
        )


async def test_deleting_marks_the_category_and_announces_it():
    repository = _repository()
    outbox = FakeOutboxRepository()

    deleted, _ = await DeleteCategoryCommandHandler(repository, outbox).handle(
        DeleteCategoryCommand(USER_ID, "user_abc", OWN_COFFEE)
    )

    assert deleted.deleted_at is not None
    assert repository.saved[0].deleted_at is not None
    assert outbox.entries[0].event_type == "CategoryDeleted"


async def test_an_already_deleted_category_is_not_found_again():
    with pytest.raises(CategoryNotFoundError):
        await DeleteCategoryCommandHandler(_repository(), FakeOutboxRepository()).handle(
            DeleteCategoryCommand(USER_ID, "user_abc", OWN_RETIRED)
        )


class Resolver(CategoryResolverMixin):
    def __init__(self, repository: FakeCategoryRepository) -> None:
        self.use_category_repository(repository)


async def test_a_visible_category_of_the_right_kind_resolves():
    reference = await Resolver(_repository()).resolve_category(
        GLOBAL_FOOD, USER_ID, CategoryKind.TRANSACTION
    )

    assert reference == CategoryReference(id=GLOBAL_FOOD, name="Food", is_global=True)


async def test_a_wallet_category_cannot_label_a_transaction():
    with pytest.raises(CategoryKindMismatchError):
        await Resolver(_repository()).resolve_category(
            OWN_SIDE_ACCOUNT, USER_ID, CategoryKind.TRANSACTION
        )


async def test_a_deleted_category_cannot_be_assigned():
    with pytest.raises(CategoryNotFoundError):
        await Resolver(_repository()).resolve_category(
            OWN_RETIRED, USER_ID, CategoryKind.TRANSACTION
        )


async def test_no_category_resolves_to_none():
    assert (
        await Resolver(_repository()).resolve_category(None, USER_ID, CategoryKind.WALLET) is None
    )


async def test_an_unchanged_category_is_passed_through():
    unchanged = object()

    resolved = await Resolver(_repository()).resolve_category_change(
        unchanged, USER_ID, CategoryKind.TRANSACTION, unchanged=unchanged
    )

    assert resolved is unchanged
