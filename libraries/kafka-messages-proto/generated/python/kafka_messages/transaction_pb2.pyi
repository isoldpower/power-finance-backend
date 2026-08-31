from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TransactionCreated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "transaction_id", "wallet_id", "user_id", "amount", "created_at", "name", "category", "evidence_url", "origin", "chain_id", "container_kind", "currency_code")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    WALLET_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_URL_FIELD_NUMBER: _ClassVar[int]
    ORIGIN_FIELD_NUMBER: _ClassVar[int]
    CHAIN_ID_FIELD_NUMBER: _ClassVar[int]
    CONTAINER_KIND_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    transaction_id: str
    wallet_id: str
    user_id: int
    amount: str
    created_at: _timestamp_pb2.Timestamp
    name: str
    category: str
    evidence_url: str
    origin: str
    chain_id: str
    container_kind: str
    currency_code: str
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., transaction_id: _Optional[str] = ..., wallet_id: _Optional[str] = ..., user_id: _Optional[int] = ..., amount: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., name: _Optional[str] = ..., category: _Optional[str] = ..., evidence_url: _Optional[str] = ..., origin: _Optional[str] = ..., chain_id: _Optional[str] = ..., container_kind: _Optional[str] = ..., currency_code: _Optional[str] = ...) -> None: ...

class TransactionDeleted(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "transaction_id", "wallet_id", "user_id", "amount", "created_at", "deleted_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    WALLET_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    transaction_id: str
    wallet_id: str
    user_id: int
    amount: str
    created_at: _timestamp_pb2.Timestamp
    deleted_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., transaction_id: _Optional[str] = ..., wallet_id: _Optional[str] = ..., user_id: _Optional[int] = ..., amount: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., deleted_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class TransactionUpdated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "transaction_id", "wallet_id", "user_id", "previous_amount", "new_amount", "updated_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    WALLET_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    NEW_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    transaction_id: str
    wallet_id: str
    user_id: int
    previous_amount: str
    new_amount: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., transaction_id: _Optional[str] = ..., wallet_id: _Optional[str] = ..., user_id: _Optional[int] = ..., previous_amount: _Optional[str] = ..., new_amount: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class TransactionMetadataUpdated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "transaction_id", "user_id", "name", "category", "evidence_url", "updated_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_URL_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    transaction_id: str
    user_id: int
    name: str
    category: str
    evidence_url: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., transaction_id: _Optional[str] = ..., user_id: _Optional[int] = ..., name: _Optional[str] = ..., category: _Optional[str] = ..., evidence_url: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
