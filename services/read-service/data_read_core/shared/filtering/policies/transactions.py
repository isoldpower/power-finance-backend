from ..entities import FilterFieldPolicy, FilterPolicy, TypeVariant

TRANSACTION_FILTER_POLICY: FilterPolicy = {
    "wallet_id": FilterFieldPolicy(
        request_name="wallet_id",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.UUID,
        es_field="wallet_id",
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
