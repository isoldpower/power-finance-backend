SANDBOX_GROUP_ID_SEPARATOR = "-sbx-"


def resolve_sandbox_scoped_group_id(group_id: str, sandbox_id: str | None) -> str:
    if not sandbox_id:
        return group_id

    return f"{group_id}{SANDBOX_GROUP_ID_SEPARATOR}{sandbox_id}"
