from typing import Any

from ..entities import FilterPolicy
from ..exceptions import ROOT_PATH
from .node import Record
from .parser import build_root


def matches(
    raw: Any,
    record: Record,
    policy: FilterPolicy,
    path: str = ROOT_PATH,
) -> bool:
    return build_root(raw, policy, path).matches(record)
