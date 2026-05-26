class InProcessLoopState:
    def __init__(self) -> None:
        self._is_complete = False
        self._last_retryable_exception: BaseException | None = None

    def mark_complete(self) -> None:
        self._is_complete = True

    def record_retryable_exception(self, exception: BaseException) -> None:
        self._last_retryable_exception = exception

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def last_retryable_exception(self) -> BaseException | None:
        return self._last_retryable_exception
