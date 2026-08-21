from collections.abc import Mapping
from types import MappingProxyType

from ..cursors import PageDirection
from .backward_scan import BackwardScan
from .forward_scan import ForwardScan
from .page_scan import PageScan

SCANS: Mapping[PageDirection, PageScan] = MappingProxyType(
    {scan.direction: scan for scan in (ForwardScan(), BackwardScan())}
)


def scan_for_direction(direction: PageDirection) -> PageScan:
    return SCANS[direction]
