from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ActionSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACTION_SOURCE_UNSPECIFIED: _ClassVar[ActionSource]
    ACTION_SOURCE_ASSISTANT: _ClassVar[ActionSource]
    ACTION_SOURCE_SCHEDULER: _ClassVar[ActionSource]

class ActionSeverity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACTION_SEVERITY_UNSPECIFIED: _ClassVar[ActionSeverity]
    ACTION_SEVERITY_INFO: _ClassVar[ActionSeverity]
    ACTION_SEVERITY_WARNING: _ClassVar[ActionSeverity]
    ACTION_SEVERITY_CRITICAL: _ClassVar[ActionSeverity]

class ActionStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACTION_STATUS_UNSPECIFIED: _ClassVar[ActionStatus]
    ACTION_STATUS_PENDING: _ClassVar[ActionStatus]
    ACTION_STATUS_RESOLVED: _ClassVar[ActionStatus]
    ACTION_STATUS_DISMISSED: _ClassVar[ActionStatus]
    ACTION_STATUS_EXPIRED: _ClassVar[ActionStatus]

class ResolutionIntent(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESOLUTION_INTENT_UNSPECIFIED: _ClassVar[ResolutionIntent]
    RESOLUTION_INTENT_PRIMARY: _ClassVar[ResolutionIntent]
    RESOLUTION_INTENT_SECONDARY: _ClassVar[ResolutionIntent]
    RESOLUTION_INTENT_DANGER: _ClassVar[ResolutionIntent]
ACTION_SOURCE_UNSPECIFIED: ActionSource
ACTION_SOURCE_ASSISTANT: ActionSource
ACTION_SOURCE_SCHEDULER: ActionSource
ACTION_SEVERITY_UNSPECIFIED: ActionSeverity
ACTION_SEVERITY_INFO: ActionSeverity
ACTION_SEVERITY_WARNING: ActionSeverity
ACTION_SEVERITY_CRITICAL: ActionSeverity
ACTION_STATUS_UNSPECIFIED: ActionStatus
ACTION_STATUS_PENDING: ActionStatus
ACTION_STATUS_RESOLVED: ActionStatus
ACTION_STATUS_DISMISSED: ActionStatus
ACTION_STATUS_EXPIRED: ActionStatus
RESOLUTION_INTENT_UNSPECIFIED: ResolutionIntent
RESOLUTION_INTENT_PRIMARY: ResolutionIntent
RESOLUTION_INTENT_SECONDARY: ResolutionIntent
RESOLUTION_INTENT_DANGER: ResolutionIntent

class ActionResolution(_message.Message):
    __slots__ = ("resolution_id", "label", "intent", "applies", "dismissal")
    RESOLUTION_ID_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    INTENT_FIELD_NUMBER: _ClassVar[int]
    APPLIES_FIELD_NUMBER: _ClassVar[int]
    DISMISSAL_FIELD_NUMBER: _ClassVar[int]
    resolution_id: str
    label: str
    intent: ResolutionIntent
    applies: bool
    dismissal: bool
    def __init__(self, resolution_id: _Optional[str] = ..., label: _Optional[str] = ..., intent: _Optional[_Union[ResolutionIntent, str]] = ..., applies: bool = ..., dismissal: bool = ...) -> None: ...

class ActionRaised(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "action_id", "user_external_id", "user_id", "source", "kind", "severity", "title", "body", "subject_type", "subject_id", "money_amount", "money_currency", "group_key", "occurrences", "last_seen_at", "expires_at", "resolutions", "created_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    ACTION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    MONEY_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    MONEY_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    GROUP_KEY_FIELD_NUMBER: _ClassVar[int]
    OCCURRENCES_FIELD_NUMBER: _ClassVar[int]
    LAST_SEEN_AT_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    RESOLUTIONS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    action_id: str
    user_external_id: str
    user_id: int
    source: ActionSource
    kind: str
    severity: ActionSeverity
    title: str
    body: str
    subject_type: str
    subject_id: str
    money_amount: str
    money_currency: str
    group_key: str
    occurrences: int
    last_seen_at: _timestamp_pb2.Timestamp
    expires_at: _timestamp_pb2.Timestamp
    resolutions: _containers.RepeatedCompositeFieldContainer[ActionResolution]
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., action_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., source: _Optional[_Union[ActionSource, str]] = ..., kind: _Optional[str] = ..., severity: _Optional[_Union[ActionSeverity, str]] = ..., title: _Optional[str] = ..., body: _Optional[str] = ..., subject_type: _Optional[str] = ..., subject_id: _Optional[str] = ..., money_amount: _Optional[str] = ..., money_currency: _Optional[str] = ..., group_key: _Optional[str] = ..., occurrences: _Optional[int] = ..., last_seen_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., resolutions: _Optional[_Iterable[_Union[ActionResolution, _Mapping]]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ActionResolved(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "action_id", "user_external_id", "user_id", "status", "resolution_id", "resolved_at", "updated_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    ACTION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_ID_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    action_id: str
    user_external_id: str
    user_id: int
    status: ActionStatus
    resolution_id: str
    resolved_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., action_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., status: _Optional[_Union[ActionStatus, str]] = ..., resolution_id: _Optional[str] = ..., resolved_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
