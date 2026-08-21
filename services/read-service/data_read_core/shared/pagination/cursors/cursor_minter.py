from dataclasses import dataclass
from typing import Any

from ..ordering import SortOrder
from .cursor_codec import CURSOR_CODEC, CursorCodec
from .page_direction import PageDirection


@dataclass(frozen=True)
class CursorMinter:
    order: SortOrder
    fingerprint: str
    codec: CursorCodec = CURSOR_CODEC

    def toward_next(self, row: Any) -> str:
        return self._mint(PageDirection.NEXT, row)

    def toward_previous(self, row: Any) -> str:
        return self._mint(PageDirection.PREVIOUS, row)

    def _mint(self, direction: PageDirection, row: Any) -> str:
        return self.codec.encode(direction, self.order.to_cursor_values(row), self.fingerprint)
