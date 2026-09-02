from data_read_core.shared.query_results import FetchedResource

from .dtos import AutomationDTO, GetAutomationQuery
from .exceptions import AutomationNotFoundError
from .infra import fetch_owned_automation


class GetAutomationQueryHandler:
    async def handle(self, query: GetAutomationQuery) -> FetchedResource:
        found = await fetch_owned_automation(query.user_id, query.automation_id)
        if found is None:
            raise AutomationNotFoundError()

        return FetchedResource(
            resource=AutomationDTO.from_read_model(found),
            cached=False,
        )
