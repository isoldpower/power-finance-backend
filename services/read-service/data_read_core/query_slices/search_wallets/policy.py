from data_read_core.shared.filtering import FilterFieldPolicy, FilterPolicy, TypeVariant

WALLET_FILTER_POLICY: FilterPolicy = {
    "name": FilterFieldPolicy(
        request_name="name",
        allowed_operators={"eq", "neq", "icontains", "contains", "in"},
        value_type=TypeVariant.STRING,
        es_field="title.keyword",
    ),
    "currency": FilterFieldPolicy(
        request_name="currency",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.STRING,
        es_field="currency_code",
    ),
    "balance": FilterFieldPolicy(
        request_name="balance",
        allowed_operators={"eq", "gte", "lte", "gt", "lt"},
        value_type=TypeVariant.FLOAT,
        es_field="balance",
    ),
    "created_at": FilterFieldPolicy(
        request_name="created_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        es_field="created_at",
    ),
}
