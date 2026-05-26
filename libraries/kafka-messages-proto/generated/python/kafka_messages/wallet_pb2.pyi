from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import timestamp_pb2 as _timestamp_pb2

DESCRIPTOR: _descriptor.FileDescriptor

class WalletCreated(_message.Message):
    __slots__ = (
        "event_id",
        "occurred_at",
        "schema_version",
        "wallet_id",
        "user_id",
        "title",
        "currency_code",
        "created_at",
    )
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    WALLET_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    wallet_id: str
    user_id: int
    title: str
    currency_code: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        event_id: str | None = ...,
        occurred_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
        schema_version: int | None = ...,
        wallet_id: str | None = ...,
        user_id: int | None = ...,
        title: str | None = ...,
        currency_code: str | None = ...,
        created_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class WalletDeleted(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "wallet_id", "user_id", "deleted_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    WALLET_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    wallet_id: str
    user_id: int
    deleted_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        event_id: str | None = ...,
        occurred_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
        schema_version: int | None = ...,
        wallet_id: str | None = ...,
        user_id: int | None = ...,
        deleted_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class WalletUpdated(_message.Message):
    __slots__ = (
        "event_id",
        "occurred_at",
        "schema_version",
        "wallet_id",
        "user_id",
        "previous_title",
        "new_title",
        "updated_at",
    )
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    WALLET_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_TITLE_FIELD_NUMBER: _ClassVar[int]
    NEW_TITLE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    wallet_id: str
    user_id: int
    previous_title: str
    new_title: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        event_id: str | None = ...,
        occurred_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
        schema_version: int | None = ...,
        wallet_id: str | None = ...,
        user_id: int | None = ...,
        previous_title: str | None = ...,
        new_title: str | None = ...,
        updated_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...
