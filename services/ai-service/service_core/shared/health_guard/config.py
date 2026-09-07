from enum import StrEnum

from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError


class ProbeName(StrEnum):
    POSTGRES = "postgres[ai]"


POSTGRES_CONNECTIVITY_ERRORS: tuple[type[BaseException], ...] = (
    OperationalError,
    InterfaceError,
    OSError,
)

PROBE_FAILURES: tuple[type[BaseException], ...] = (
    *POSTGRES_CONNECTIVITY_ERRORS,
    DBAPIError,
)
