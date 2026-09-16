from ..domain.entities import AssistantQuota


def present_quota(quota: AssistantQuota) -> dict:
    return {
        "messages_left": quota.remaining,
        "allowance": quota.allowance,
    }
