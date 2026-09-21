class ApplicationError(Exception):
    pass


class FallbackTransactionNotVisibleError(ApplicationError):
    pass
