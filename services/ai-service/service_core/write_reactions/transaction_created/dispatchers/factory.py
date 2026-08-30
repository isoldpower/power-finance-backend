from collections.abc import Callable

from ..contracts import PostingDispatcher
from ..repositories import AccountRepository

DispatcherFactory = Callable[
    [AccountRepository],
    PostingDispatcher,
]
