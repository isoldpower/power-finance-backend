from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AccountGroup(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCOUNT_GROUP_WRONG: _ClassVar[AccountGroup]
    ACCOUNT_GROUP_ASSETS: _ClassVar[AccountGroup]
    ACCOUNT_GROUP_LIABILITIES: _ClassVar[AccountGroup]
    ACCOUNT_GROUP_EQUITY: _ClassVar[AccountGroup]
ACCOUNT_GROUP_WRONG: AccountGroup
ACCOUNT_GROUP_ASSETS: AccountGroup
ACCOUNT_GROUP_LIABILITIES: AccountGroup
ACCOUNT_GROUP_EQUITY: AccountGroup

class AccountCreated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "account_id", "user_external_id", "user_id", "account_group", "name", "balance", "created_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_GROUP_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    BALANCE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    account_id: str
    user_external_id: str
    user_id: int
    account_group: AccountGroup
    name: str
    balance: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., account_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., account_group: _Optional[_Union[AccountGroup, str]] = ..., name: _Optional[str] = ..., balance: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AccountUpdated(_message.Message):
    __slots__ = ("event_id", "occurred_at", "schema_version", "account_id", "user_external_id", "user_id", "previous_balance", "new_balance", "account_group", "name", "updated_at")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_BALANCE_FIELD_NUMBER: _ClassVar[int]
    NEW_BALANCE_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_GROUP_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    occurred_at: _timestamp_pb2.Timestamp
    schema_version: int
    account_id: str
    user_external_id: str
    user_id: int
    previous_balance: str
    new_balance: str
    account_group: AccountGroup
    name: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., schema_version: _Optional[int] = ..., account_id: _Optional[str] = ..., user_external_id: _Optional[str] = ..., user_id: _Optional[int] = ..., previous_balance: _Optional[str] = ..., new_balance: _Optional[str] = ..., account_group: _Optional[_Union[AccountGroup, str]] = ..., name: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
