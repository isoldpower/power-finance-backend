import json
from typing import Any

from .config import COMPACT_SEPARATORS


def dump_compact(payload: Any, *, sort_keys: bool = False) -> str:
    return json.dumps(payload, sort_keys=sort_keys, separators=COMPACT_SEPARATORS, default=str)
