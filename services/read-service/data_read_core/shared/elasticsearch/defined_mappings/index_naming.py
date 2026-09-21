import os

ENVIRONMENT_VARIABLE_INDEX_PREFIX = "ELASTICSEARCH_INDEX_PREFIX"


def resolve_index_name_prefix() -> str:
    return os.environ.get(ENVIRONMENT_VARIABLE_INDEX_PREFIX, "").strip()


def build_index_name(base_index_name: str) -> str:
    return f"{resolve_index_name_prefix()}{base_index_name}"
