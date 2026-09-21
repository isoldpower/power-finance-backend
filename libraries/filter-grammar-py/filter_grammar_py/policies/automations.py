from ..entities import FilterFieldPolicy, FilterPolicy, TypeVariant

AUTOMATION_FILTER_POLICY: FilterPolicy = {
    "name": FilterFieldPolicy(
        request_name="name",
        allowed_operators={"eq", "neq", "in", "contains", "icontains"},
        value_type=TypeVariant.STRING,
        model_lookup="name",
        es_field="name.keyword",
    ),
    "enabled": FilterFieldPolicy(
        request_name="enabled",
        allowed_operators={"eq", "neq"},
        value_type=TypeVariant.BOOLEAN,
        model_lookup="enabled",
        es_field="enabled",
    ),
    "trigger_type": FilterFieldPolicy(
        request_name="trigger_type",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.STRING,
        model_lookup="trigger_type",
        es_field="trigger_type",
    ),
    "trigger_event": FilterFieldPolicy(
        request_name="trigger_event",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.STRING,
        model_lookup="trigger_event",
        es_field="trigger_event",
    ),
    "trigger_schedule": FilterFieldPolicy(
        request_name="trigger_schedule",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.STRING,
        model_lookup="trigger_schedule",
        es_field="trigger_schedule",
    ),
    "runs": FilterFieldPolicy(
        request_name="runs",
        allowed_operators={"eq", "gte", "lte", "gt", "lt"},
        value_type=TypeVariant.INTEGER,
        model_lookup="runs",
        es_field="runs",
    ),
    "last_run_at": FilterFieldPolicy(
        request_name="last_run_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        model_lookup="last_run_at",
        es_field="last_run_at",
    ),
    "created_at": FilterFieldPolicy(
        request_name="created_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
        model_lookup="created_at",
        es_field="created_at",
    ),
}
