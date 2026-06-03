from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class UserSynced(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "user_id", "external_id")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    user_id: int
    external_id: str
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., user_id: _Optional[int] = ..., external_id: _Optional[str] = ...) -> None: ...
