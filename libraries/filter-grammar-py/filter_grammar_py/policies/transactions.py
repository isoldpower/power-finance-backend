from ..entities import FilterFieldPolicy, FilterPolicy, TypeVariant

TRANSACTION_FILTER_POLICY: FilterPolicy = {
    "wallet_id": FilterFieldPolicy(
        request_name="wallet_id",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.UUID,
        es_field="wallet_id",
    ),
    "chain_id": FilterFieldPolicy(
        request_name="chain_id",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.UUID,
        es_field="chain_id",
    ),
    "amount": FilterFieldPolicy(
        request_name="amount",
        allowed_operators={"eq", "gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DECIMAL,
        es_field="amount",
    ),
    "currency": FilterFieldPolicy(
        request_name="currency",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.STRING,
        model_lookup="currency_code",
        es_field="currency_code",
    ),
    "name": FilterFieldPolicy(
        request_name="name",
        allowed_operators={"eq", "neq", "in", "contains", "icontains"},
        value_type=TypeVariant.STRING,
        es_field="name.keyword",
    ),
    "category": FilterFieldPolicy(
        request_name="category",
        allowed_operators={"eq", "neq", "in", "contains", "icontains"},
        value_type=TypeVariant.STRING,
        es_field="category.keyword",
    ),
    "type": FilterFieldPolicy(
        request_name="type",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.STRING,
        es_field="type",
    ),
    "origin": FilterFieldPolicy(
        request_name="origin",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.STRING,
        es_field="origin",
    ),
    "created_at": FilterFieldPolicy(
        request_name="created_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        es_field="created_at",
    ),
    "occurred_at": FilterFieldPolicy(
        request_name="occurred_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        es_field="occurred_at",
    ),
}
