from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

UNREACHABLE: tuple[type[BaseException], ...] = (
    OperationalError,
    InterfaceError,
    OSError,
    DBAPIError,
)
