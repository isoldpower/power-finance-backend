from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from ...dtos import WebhookDeliveryDTO, WebhookDeliveryAttemptDTO


@dataclass(frozen=True)
class CreateWebhookDeliveryData:
    endpoint_id: UUID
    event_id: UUID


@dataclass(frozen=True)
class CreateWebhookDeliveryAttemptData:
    delivery_id: UUID
    request_headers: dict
    request_body: dict


@dataclass(frozen=True)
class FinalizeWebhookDeliveryAttemptData:
    attempt_id: int
    response_status: int
    response_body: str
    error_message: str | None


class WebhookDeliveryRepository(ABC):
    @abstractmethod
    def get_delivery_by_id(self, webhook_id: UUID, event_id: UUID, user_id: int) -> WebhookDeliveryDTO:
        raise NotImplementedError()

    @abstractmethod
    def create_delivery(self, data: CreateWebhookDeliveryData) -> WebhookDeliveryDTO:
        raise NotImplementedError()

    @abstractmethod
    def create_delivery_attempt(self, data: CreateWebhookDeliveryAttemptData) -> WebhookDeliveryAttemptDTO:
        raise NotImplementedError()

    @abstractmethod
    def finalize_delivery_attempt(self, data: FinalizeWebhookDeliveryAttemptData) -> WebhookDeliveryAttemptDTO:
        raise NotImplementedError()

    @abstractmethod
    def get_deliveries_to_retry(self, limit: int) -> list[WebhookDeliveryDTO]:
        raise NotImplementedError()

    @abstractmethod
    def mark_delivery_in_progress(self, delivery_id: UUID) -> WebhookDeliveryDTO:
        raise NotImplementedError()

    @abstractmethod
    def mark_delivery_success(self, delivery_id: UUID) -> WebhookDeliveryDTO:
        raise NotImplementedError()

    @abstractmethod
    def mark_delivery_retry_scheduled(
            self,
            delivery_id: UUID,
            error_message: str | None,
            retry_in: timedelta
    ) -> WebhookDeliveryDTO:
        raise NotImplementedError()

    @abstractmethod
    def mark_delivery_failed(
            self,
            delivery_id: UUID,
            error_message: str | None
    ) -> WebhookDeliveryDTO:
        raise NotImplementedError()
