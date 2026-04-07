import json
from dataclasses import dataclass

from finances.application.interfaces import NetworkSender, MessageResponse
from finances.domain.entities import Webhook


@dataclass(frozen=True)
class RequestStamp:
    request_body: dict
    request_headers: dict


class WebhookDispatcher:
    _sender: NetworkSender

    def __init__(
            self,
            sender: NetworkSender
    ) -> None:
        self._sender = sender

    def get_request_data(
            self,
            webhook: Webhook,
            event_type: str,
            payload: dict
    ) -> RequestStamp:
        request_body: dict = payload
        request_headers: dict = {
            'Content-Type': 'application/json',
            'X-Webhook-Event': event_type,
            'X-Webhook-Encoded': webhook.sign_payload(
                json.dumps(obj=payload, sort_keys=True)
            )
        }

        return RequestStamp(
            request_body=request_body,
            request_headers=request_headers,
        )

    def dispatch_request(
            self,
            webhook: Webhook,
            request_stamp: RequestStamp,
    ) -> MessageResponse:
        return self._sender.send_message_with_body(
            url=webhook.url,
            request_body=request_stamp.request_body,
            request_headers=request_stamp.request_headers,
        )
