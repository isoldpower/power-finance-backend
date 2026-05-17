from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MessageResultInfo:
    message: str
    resource_id: str | None


class CommonHttpPresenter:
    @staticmethod
    def present_message_result(info: MessageResultInfo) -> dict[str, Any]:
        return {
            "message": info.message,
            "meta": {
                "id": info.resource_id,
            },
        }
