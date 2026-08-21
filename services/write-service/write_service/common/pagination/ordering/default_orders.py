from .sort_direction import SortDirection
from .sort_key import SortKey
from .sort_order import SortOrder
from .value_codecs import DATETIME_CODEC, UUID_CODEC

CREATED_AT_DESC = SortOrder(
    keys=(
        SortKey("created_at", SortDirection.DESCENDING, DATETIME_CODEC),
        SortKey("id", SortDirection.DESCENDING, UUID_CODEC),
    )
)
