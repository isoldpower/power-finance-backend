class ApplicationError(Exception):
    """Base class for application-layer (use-case / query) errors.

    Mirrors `domain.exceptions.DomainError`: each layer raises through its own
    base so callers can catch a whole layer's failures with one `except`.
    """


class FallbackTransactionNotVisibleError(ApplicationError):
    """The ledger row is not a standalone user-facing transaction."""
