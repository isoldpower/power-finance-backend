from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AutomationEffect(_message.Message):
    __slots__ = ("effect_type", "params_json")
    EFFECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    PARAMS_JSON_FIELD_NUMBER: _ClassVar[int]
    effect_type: str
    params_json: str
    def __init__(self, effect_type: _Optional[str] = ..., params_json: _Optional[str] = ...) -> None: ...

class AutomationTrigger(_message.Message):
    __slots__ = ("trigger_type", "event", "schedule", "filter_body_json")
    TRIGGER_TYPE_FIELD_NUMBER: _ClassVar[int]
    EVENT_FIELD_NUMBER: _ClassVar[int]
    SCHEDULE_FIELD_NUMBER: _ClassVar[int]
    FILTER_BODY_JSON_FIELD_NUMBER: _ClassVar[int]
    trigger_type: str
    event: str
    schedule: str
    filter_body_json: str
    def __init__(self, trigger_type: _Optional[str] = ..., event: _Optional[str] = ..., schedule: _Optional[str] = ..., filter_body_json: _Optional[str] = ...) -> None: ...

class AutomationCreated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "automation_id", "user_external_id", "user_id", "name", "icon", "enabled", "trigger", "effects", "created_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    AUTOMATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ICON_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    EFFECTS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    automation_id: str
    user_external_id: str
    user_id: int
    name: str
    icon: str
    enabled: bool
    trigger: AutomationTrigger
    effects: _containers.RepeatedCompositeFieldContainer[AutomationEffect]
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., automation_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., name: _Optional[str] = ..., icon: _Optional[str] = ..., enabled: bool = ..., trigger: _Optional[_Union[AutomationTrigger, _Mapping]] = ..., effects: _Optional[_Iterable[_Union[AutomationEffect, _Mapping]]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AutomationUpdated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "automation_id", "user_external_id", "user_id", "name", "icon", "enabled", "trigger", "effects", "updated_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    AUTOMATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ICON_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    EFFECTS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    automation_id: str
    user_external_id: str
    user_id: int
    name: str
    icon: str
    enabled: bool
    trigger: AutomationTrigger
    effects: _containers.RepeatedCompositeFieldContainer[AutomationEffect]
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., automation_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., name: _Optional[str] = ..., icon: _Optional[str] = ..., enabled: bool = ..., trigger: _Optional[_Union[AutomationTrigger, _Mapping]] = ..., effects: _Optional[_Iterable[_Union[AutomationEffect, _Mapping]]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AutomationDeleted(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "automation_id", "user_external_id", "user_id", "deleted_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    AUTOMATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    automation_id: str
    user_external_id: str
    user_id: int
    deleted_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., automation_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., deleted_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AutomationRan(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "automation_id", "user_external_id", "user_id", "runs", "last_run_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    AUTOMATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    RUNS_FIELD_NUMBER: _ClassVar[int]
    LAST_RUN_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    automation_id: str
    user_external_id: str
    user_id: int
    runs: int
    last_run_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., automation_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., runs: _Optional[int] = ..., last_run_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
