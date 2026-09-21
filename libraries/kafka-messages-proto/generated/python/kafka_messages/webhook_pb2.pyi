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

class WebhookEndpointCreated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "webhook_id", "user_id", "title", "url", "secret", "created_at", "secret_version", "enabled")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    SECRET_VERSION_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    webhook_id: str
    user_id: int
    title: str
    url: str
    secret: str
    created_at: _timestamp_pb2.Timestamp
    secret_version: int
    enabled: bool
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., webhook_id: _Optional[str] = ..., user_id: _Optional[int] = ..., title: _Optional[str] = ..., url: _Optional[str] = ..., secret: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., secret_version: _Optional[int] = ..., enabled: bool = ...) -> None: ...

class WebhookEndpointUpdated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "webhook_id", "user_id", "title", "url", "updated_at", "enabled")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    webhook_id: str
    user_id: int
    title: str
    url: str
    updated_at: _timestamp_pb2.Timestamp
    enabled: bool
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., webhook_id: _Optional[str] = ..., user_id: _Optional[int] = ..., title: _Optional[str] = ..., url: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., enabled: bool = ...) -> None: ...

class WebhookEndpointDeleted(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "webhook_id", "user_id", "deleted_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    webhook_id: str
    user_id: int
    deleted_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., webhook_id: _Optional[str] = ..., user_id: _Optional[int] = ..., deleted_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class WebhookSecretRotated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "webhook_id", "user_id", "secret", "rotated_at", "previous_secret", "secret_version", "previous_secret_version", "previous_secret_expires_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    ROTATED_AT_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_SECRET_FIELD_NUMBER: _ClassVar[int]
    SECRET_VERSION_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_SECRET_VERSION_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_SECRET_EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    webhook_id: str
    user_id: int
    secret: str
    rotated_at: _timestamp_pb2.Timestamp
    previous_secret: str
    secret_version: int
    previous_secret_version: int
    previous_secret_expires_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., webhook_id: _Optional[str] = ..., user_id: _Optional[int] = ..., secret: _Optional[str] = ..., rotated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., previous_secret: _Optional[str] = ..., secret_version: _Optional[int] = ..., previous_secret_version: _Optional[int] = ..., previous_secret_expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class WebhookSubscriptionAdded(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "subscription_id", "webhook_id", "user_id", "event_type", "created_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    SUBSCRIPTION_ID_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    subscription_id: str
    webhook_id: str
    user_id: int
    event_type: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., subscription_id: _Optional[str] = ..., webhook_id: _Optional[str] = ..., user_id: _Optional[int] = ..., event_type: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class WebhookSubscriptionRemoved(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "subscription_id", "webhook_id", "user_id", "removed_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    SUBSCRIPTION_ID_FIELD_NUMBER: _ClassVar[int]
    WEBHOOK_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    REMOVED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    subscription_id: str
    webhook_id: str
    user_id: int
    removed_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., subscription_id: _Optional[str] = ..., webhook_id: _Optional[str] = ..., user_id: _Optional[int] = ..., removed_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
