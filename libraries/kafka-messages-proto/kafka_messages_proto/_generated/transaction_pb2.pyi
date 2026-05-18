from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TransactionCreated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "transaction_id", "wallet_id", "user_id", "amount", "created_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    WALLET_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    transaction_id: str
    wallet_id: str
    user_id: int
    amount: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., transaction_id: _Optional[str] = ..., wallet_id: _Optional[str] = ..., user_id: _Optional[int] = ..., amount: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class TransactionDeleted(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "transaction_id", "wallet_id", "user_id", "amount", "cancelled_by", "created_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    WALLET_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CANCELLED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    transaction_id: str
    wallet_id: str
    user_id: int
    amount: str
    cancelled_by: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., transaction_id: _Optional[str] = ..., wallet_id: _Optional[str] = ..., user_id: _Optional[int] = ..., amount: _Optional[str] = ..., cancelled_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
