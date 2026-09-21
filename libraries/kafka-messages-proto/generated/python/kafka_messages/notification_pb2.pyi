from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class NotificationSeverity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOTIFICATION_SEVERITY_UNSPECIFIED: _ClassVar[NotificationSeverity]
    NOTIFICATION_SEVERITY_INFO: _ClassVar[NotificationSeverity]
    NOTIFICATION_SEVERITY_WARNING: _ClassVar[NotificationSeverity]
    NOTIFICATION_SEVERITY_CRITICAL: _ClassVar[NotificationSeverity]
NOTIFICATION_SEVERITY_UNSPECIFIED: NotificationSeverity
NOTIFICATION_SEVERITY_INFO: NotificationSeverity
NOTIFICATION_SEVERITY_WARNING: NotificationSeverity
NOTIFICATION_SEVERITY_CRITICAL: NotificationSeverity

class NotificationRequested(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "user_id", "user_external_id", "title", "body", "payload", "severity", "subject_type", "subject_id")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    user_id: int
    user_external_id: str
    title: str
    body: str
    payload: _struct_pb2.Struct
    severity: NotificationSeverity
    subject_type: str
    subject_id: str
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., user_id: _Optional[int] = ..., user_external_id: _Optional[str] = ..., title: _Optional[str] = ..., body: _Optional[str] = ..., payload: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., severity: _Optional[_Union[NotificationSeverity, str]] = ..., subject_type: _Optional[str] = ..., subject_id: _Optional[str] = ...) -> None: ...

class NotificationCreated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "notification_id", "user_id", "title", "body", "payload", "created_at", "severity", "subject_type", "subject_id", "user_external_id")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    NOTIFICATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    notification_id: str
    user_id: int
    title: str
    body: str
    payload: _struct_pb2.Struct
    created_at: _timestamp_pb2.Timestamp
    severity: NotificationSeverity
    subject_type: str
    subject_id: str
    user_external_id: str
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., notification_id: _Optional[str] = ..., user_id: _Optional[int] = ..., title: _Optional[str] = ..., body: _Optional[str] = ..., payload: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., severity: _Optional[_Union[NotificationSeverity, str]] = ..., subject_type: _Optional[str] = ..., subject_id: _Optional[str] = ..., user_external_id: _Optional[str] = ...) -> None: ...

class NotificationsAcknowledged(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "notification_ids", "user_id", "acknowledged_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    NOTIFICATION_IDS_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ACKNOWLEDGED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    notification_ids: _containers.RepeatedScalarFieldContainer[str]
    user_id: int
    acknowledged_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., notification_ids: _Optional[_Iterable[str]] = ..., user_id: _Optional[int] = ..., acknowledged_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class NotificationDeleted(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "notification_id", "user_id", "deleted_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    NOTIFICATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    notification_id: str
    user_id: int
    deleted_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., notification_id: _Optional[str] = ..., user_id: _Optional[int] = ..., deleted_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
