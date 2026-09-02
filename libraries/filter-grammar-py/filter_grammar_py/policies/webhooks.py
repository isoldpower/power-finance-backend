from ..entities import FilterFieldPolicy, FilterPolicy, TypeVariant

WEBHOOK_FILTER_POLICY: FilterPolicy = {
    "title": FilterFieldPolicy(
        request_name="title",
        allowed_operators={"eq", "neq", "in", "contains", "icontains"},
        value_type=TypeVariant.STRING,
        model_lookup="title",
    ),
    "url": FilterFieldPolicy(
        request_name="url",
        allowed_operators={"eq", "neq", "contains", "icontains"},
        value_type=TypeVariant.STRING,
        model_lookup="url",
    ),
    "is_active": FilterFieldPolicy(
        request_name="is_active",
        allowed_operators={"eq", "neq"},
        value_type=TypeVariant.BOOLEAN,
        model_lookup="is_active",
    ),
    "created_at": FilterFieldPolicy(
        request_name="created_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        model_lookup="created_at",
    ),
}
