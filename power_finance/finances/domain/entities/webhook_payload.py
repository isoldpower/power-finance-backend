import hashlib
import json
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class WebhookPayload:
    id: UUID
    payload: dict
    headers: dict
    delivery_id: UUID

    @property
    def hash(self) -> str:
        encoded_payload = json.dumps(self.payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        encoded_headers = json.dumps(self.headers, sort_keys=True, separators=(',', ':')).encode('utf-8')
        encoded_data = encoded_payload + encoded_headers

        return hashlib.sha256(encoded_data).hexdigest()

    @classmethod
    def create(
            cls,
            payload: dict,
            headers: dict,
            delivery_id: UUID,
    ) -> 'WebhookPayload':
        return WebhookPayload(
            id=uuid4(),
            payload=payload,
            delivery_id=delivery_id,
            headers=headers,
        )
