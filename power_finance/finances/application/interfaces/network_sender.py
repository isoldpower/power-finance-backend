from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MessageResponse:
    status_code: int
    response_body: str
    response_headers: dict
    error_message: str | None


class NetworkSender(ABC):
    @abstractmethod
    def send_message_with_body(
            self,
            url: str,
            request_body: dict,
            request_headers: dict,
    ) -> MessageResponse:
        raise NotImplementedError()