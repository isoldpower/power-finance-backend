from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WebhookDeliveryStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    WEBHOOK_DELIVERY_STATUS_UNSPECIFIED: _ClassVar[WebhookDeliveryStatus]
    WEBHOOK_DELIVERY_STATUS_IN_PROGRESS: _ClassVar[WebhookDeliveryStatus]
    WEBHOOK_DELIVERY_STATUS_SUCCESS: _ClassVar[WebhookDeliveryStatus]
    WEBHOOK_DELIVERY_STATUS_FAILED: _ClassVar[WebhookDeliveryStatus]
    WEBHOOK_DELIVERY_STATUS_RETRY_SCHEDULED: _ClassVar[WebhookDeliveryStatus]
WEBHOOK_DELIVERY_STATUS_UNSPECIFIED: WebhookDeliveryStatus
WEBHOOK_DELIVERY_STATUS_IN_PROGRESS: WebhookDeliveryStatus
WEBHOOK_DELIVERY_STATUS_SUCCESS: WebhookDeliveryStatus
WEBHOOK_DELIVERY_STATUS_FAILED: WebhookDeliveryStatus
WEBHOOK_DELIVERY_STATUS_RETRY_SCHEDULED: WebhookDeliveryStatus

class WebhookDeliveryStatusChanged(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "delivery_id", "endpoint_id", "user_id", "status")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    DELIVERY_ID_FIELD_NUMBER: _ClassVar[int]
    ENDPOINT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    delivery_id: str
    endpoint_id: str
    user_id: int
    status: WebhookDeliveryStatus
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., delivery_id: _Optional[str] = ..., endpoint_id: _Optional[str] = ..., user_id: _Optional[int] = ..., status: _Optional[_Union[WebhookDeliveryStatus, str]] = ...) -> None: ...
