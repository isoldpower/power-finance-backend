from ..contracts import DatabaseHealth, DatabaseMigrations


class FakeDatabase(DatabaseHealth):
    def __init__(self, name: str, reachable: bool) -> None:
        self._name = name
        self._reachable = reachable

    @property
    def name(self) -> str:
        return self._name

    async def is_reachable(self) -> bool:
        return self._reachable


class ExplodingDatabase(DatabaseHealth):
    """A check that breaks, as opposed to a store that is merely down."""

    @property
    def name(self) -> str:
        return "postgres[ai]"

    async def is_reachable(self) -> bool:
        raise RuntimeError("the driver gave up")


class FakeMigrations(DatabaseMigrations):
    def __init__(self, *pending: str) -> None:
        self._pending = pending

    async def pending(self) -> tuple[str, ...]:
        return self._pending


class ExplodingMigrations(DatabaseMigrations):
    async def pending(self) -> tuple[str, ...]:
        raise RuntimeError("no alembic_version table")


class NeverAsked(DatabaseMigrations):
    """Fails the test if the migration chain is consulted at all."""

    async def pending(self) -> tuple[str, ...]:
        raise AssertionError("this probe must not check migrations")
