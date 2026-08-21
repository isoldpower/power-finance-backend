from dataclasses import dataclass
from typing import Any

from rest_framework.request import Request

from .config import FIRST_PAGE_CACHE_TOKEN, LOOKAHEAD_ROW_COUNT, PARAMETER_NAMES
from .cursors import CURSOR_CODEC, Cursor, CursorMinter, PageDirection, query_fingerprint
from .limit_policy import DEFAULT_LIMIT_POLICY, LimitPolicy
from .ordering import SortOrder
from .scans import PageScan, scan_for_direction


@dataclass(frozen=True)
class PageRequest:
    limit: int
    order: SortOrder
    fingerprint: str
    cursor: Cursor | None = None
    raw_cursor: str | None = None

    @property
    def direction(self) -> PageDirection:
        return self.cursor.direction if self.cursor else PageDirection.NEXT

    @property
    def scan(self) -> PageScan:
        return scan_for_direction(self.direction)

    @property
    def read_order(self) -> SortOrder:
        return self.scan.read_order(self.order)

    @property
    def anchor(self) -> list[Any] | None:
        return self.order.to_anchor_values(self.cursor.values) if self.cursor else None

    @property
    def elasticsearch_anchor(self) -> list[Any] | None:
        return self.order.to_elasticsearch_anchor(self.cursor.values) if self.cursor else None

    @property
    def cursor_minter(self) -> CursorMinter:
        return CursorMinter(order=self.order, fingerprint=self.fingerprint)

    @property
    def cache_token(self) -> str:
        return self.raw_cursor or FIRST_PAGE_CACHE_TOKEN

    @property
    def is_first_request(self) -> bool:
        return self.cursor is None

    @property
    def fetch_size(self) -> int:
        return self.limit + LOOKAHEAD_ROW_COUNT

    @classmethod
    def from_request(
        cls,
        request: Request,
        order: SortOrder,
        query_material: Any = None,
        limit_policy: LimitPolicy = DEFAULT_LIMIT_POLICY,
    ) -> "PageRequest":
        fingerprint = query_fingerprint(order, query_material)
        raw_cursor = request.query_params.get(PARAMETER_NAMES.get("CURSOR"))

        return cls(
            limit=limit_policy.resolve(request.query_params.get(PARAMETER_NAMES.get("LIMIT"))),
            order=order,
            fingerprint=fingerprint,
            cursor=CURSOR_CODEC.decode(raw_cursor, fingerprint) if raw_cursor else None,
            raw_cursor=raw_cursor,
        )
