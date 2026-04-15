from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MessageResponse:
    status_code: int
    response_body: str | None
    response_headers: dict | None
    error_message: str | None


class NetworkSender(ABC):
    @abstractmethod
    async def send_message_with_body(
            self,
            url: str,
            request_body: dict,
            request_headers: dict,
    ) -> MessageResponse:
        raise NotImplementedError()