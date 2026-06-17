class ApplicationError(Exception):
    """Base class for application-layer (use-case / query) errors. Each layer
    raises through its own base so one `except` catches the whole layer."""


class FallbackTransactionNotVisibleError(ApplicationError):
    """The ledger row is not a standalone user-facing transaction."""
