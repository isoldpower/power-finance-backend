from ..entities import FilterFieldPolicy, FilterPolicy, TypeVariant

WALLET_FILTER_POLICY: FilterPolicy = {
    "name": FilterFieldPolicy(
        request_name="name",
        allowed_operators={"eq", "neq", "in", "contains", "icontains"},
        value_type=TypeVariant.STRING,
        model_lookup="title",
        es_field="title.keyword",
    ),
    "currency": FilterFieldPolicy(
        request_name="currency",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.STRING,
        model_lookup="currency_code",
        es_field="currency_code",
    ),
    "balance": FilterFieldPolicy(
        request_name="balance",
        allowed_operators={"eq", "gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DECIMAL,
        es_field="balance",
    ),
    "created_at": FilterFieldPolicy(
        request_name="created_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        es_field="created_at",
    ),
}
