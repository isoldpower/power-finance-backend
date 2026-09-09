from ..entities import FilterFieldPolicy, FilterPolicy, TypeVariant

GOAL_FILTER_POLICY: FilterPolicy = {
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
    "target": FilterFieldPolicy(
        request_name="target",
        allowed_operators={"eq", "gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DECIMAL,
        model_lookup="target",
        es_field="target",
    ),
    "progress": FilterFieldPolicy(
        request_name="progress",
        allowed_operators={"eq", "gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DECIMAL,
        model_lookup="progress",
        es_field="progress",
    ),
    "finish_at": FilterFieldPolicy(
        request_name="finish_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        model_lookup="finish_at",
        es_field="finish_at",
    ),
    "created_at": FilterFieldPolicy(
        request_name="created_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        model_lookup="created_at",
        es_field="created_at",
    ),
}
