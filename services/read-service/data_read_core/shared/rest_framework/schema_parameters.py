from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from data_read_core.shared.pagination import DEFAULT_LIMIT_POLICY, PARAMETER_NAMES

LIMIT_PARAMETER = OpenApiParameter(
    PARAMETER_NAMES["LIMIT"],
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description=(
        f"Page size. Defaults to {DEFAULT_LIMIT_POLICY.default}, clamped to "
        f"{DEFAULT_LIMIT_POLICY.minimum}..{DEFAULT_LIMIT_POLICY.maximum} — out-of-range values "
        "are clamped rather than rejected, so `meta.limit` reports what was applied."
    ),
)

CURSOR_PARAMETER = OpenApiParameter(
    PARAMETER_NAMES["CURSOR"],
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description=(
        "Opaque cursor from a previous response's `meta.next_cursor` or "
        "`meta.prev_cursor`. Absent returns the first page. Direction is encoded "
        "in the cursor itself."
    ),
)
