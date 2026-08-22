from .sort_direction import SortDirection
from .sort_key import SortKey
from .sort_order import SortOrder
from .value_codecs import BOOLEAN_CODEC, DATETIME_CODEC, UUID_CODEC

CREATED_AT_DESC = SortOrder(
    keys=(
        SortKey("created_at", SortDirection.DESCENDING, DATETIME_CODEC),
        SortKey("id", SortDirection.DESCENDING, UUID_CODEC),
    )
)

FAVORITE_CREATED_AT_DESC = SortOrder(
    keys=(
        SortKey("favorite", SortDirection.DESCENDING, BOOLEAN_CODEC),
        SortKey("created_at", SortDirection.DESCENDING, DATETIME_CODEC),
        SortKey("id", SortDirection.DESCENDING, UUID_CODEC),
    )
)

TRANSACTION_FEED = SortOrder(
    keys=(
        SortKey("created_at", SortDirection.DESCENDING, DATETIME_CODEC),
        SortKey("chain_sort", SortDirection.ASCENDING, UUID_CODEC),
        SortKey("id", SortDirection.DESCENDING, UUID_CODEC),
    )
)
