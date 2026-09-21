from data_read_core.shared.postgres_orm import AutomationReadModel


async def fetch_owned_automation(user_id: int, automation_id: str) -> AutomationReadModel | None:
    return await AutomationReadModel.objects.filter(
        id=automation_id,
        user_id=user_id,
    ).afirst()
