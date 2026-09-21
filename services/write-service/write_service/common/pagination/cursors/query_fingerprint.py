import hashlib
from typing import Any

from ..ordering import SortOrder
from .compact_json import dump_compact
from .config import CursorSettings, FingerprintKey


def query_fingerprint(order: SortOrder, query_material: Any = None) -> str:
    canonical = dump_compact(
        {FingerprintKey.ORDER: order.signature, FingerprintKey.QUERY: query_material},
        sort_keys=True,
    )

    return hashlib.sha256(canonical.encode()).hexdigest()[: CursorSettings.FINGERPRINT_LENGTH]
