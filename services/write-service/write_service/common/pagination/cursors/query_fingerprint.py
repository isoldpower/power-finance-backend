import hashlib
from typing import Any

from ..ordering import SortOrder
from .compact_json import dump_compact
from .config import FINGERPRINT_LENGTH, ORDER_KEY, QUERY_KEY


def query_fingerprint(order: SortOrder, query_material: Any = None) -> str:
    """Bind a cursor to the query that produced it."""

    canonical = dump_compact(
        {ORDER_KEY: order.signature, QUERY_KEY: query_material},
        sort_keys=True,
    )

    return hashlib.sha256(canonical.encode()).hexdigest()[:FINGERPRINT_LENGTH]
