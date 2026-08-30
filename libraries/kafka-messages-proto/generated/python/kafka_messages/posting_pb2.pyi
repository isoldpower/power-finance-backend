from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AccountPostingCreated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "posting_id", "dispatch_id", "account_id", "transaction_id", "user_external_id", "user_id", "amount", "title", "icon", "debit", "currency_code", "position", "created_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    POSTING_ID_FIELD_NUMBER: _ClassVar[int]
    DISPATCH_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    ICON_FIELD_NUMBER: _ClassVar[int]
    DEBIT_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    posting_id: str
    dispatch_id: str
    account_id: str
    transaction_id: str
    user_external_id: str
    user_id: int
    amount: str
    title: str
    icon: str
    debit: bool
    currency_code: str
    position: int
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., posting_id: _Optional[str] = ..., dispatch_id: _Optional[str] = ..., account_id: _Optional[str] = ..., transaction_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., amount: _Optional[str] = ..., title: _Optional[str] = ..., icon: _Optional[str] = ..., debit: bool = ..., currency_code: _Optional[str] = ..., position: _Optional[int] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AccountPostingDeleted(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "posting_id", "dispatch_id", "account_id", "transaction_id", "user_external_id", "user_id", "deleted_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    POSTING_ID_FIELD_NUMBER: _ClassVar[int]
    DISPATCH_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    posting_id: str
    dispatch_id: str
    account_id: str
    transaction_id: str
    user_external_id: str
    user_id: int
    deleted_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., posting_id: _Optional[str] = ..., dispatch_id: _Optional[str] = ..., account_id: _Optional[str] = ..., transaction_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., deleted_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AccountPostingsDispatched(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "dispatch_id", "transaction_id", "user_external_id", "user_id", "deleted_count", "created_count", "balanced", "comment", "backend", "dispatched_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    DISPATCH_ID_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DELETED_COUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_COUNT_FIELD_NUMBER: _ClassVar[int]
    BALANCED_FIELD_NUMBER: _ClassVar[int]
    COMMENT_FIELD_NUMBER: _ClassVar[int]
    BACKEND_FIELD_NUMBER: _ClassVar[int]
    DISPATCHED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    dispatch_id: str
    transaction_id: str
    user_external_id: str
    user_id: int
    deleted_count: int
    created_count: int
    balanced: bool
    comment: str
    backend: str
    dispatched_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., dispatch_id: _Optional[str] = ..., transaction_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., deleted_count: _Optional[int] = ..., created_count: _Optional[int] = ..., balanced: bool = ..., comment: _Optional[str] = ..., backend: _Optional[str] = ..., dispatched_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
