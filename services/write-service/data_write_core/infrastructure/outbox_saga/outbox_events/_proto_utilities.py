from datetime import datetime
from typing import Any

from google.protobuf.json_format import MessageToDict
from google.protobuf.timestamp_pb2 import Timestamp


def format_timestamp_as_proto(timestamp: datetime) -> Timestamp:
    proto_timestamp = Timestamp()
    proto_timestamp.FromDatetime(timestamp)
    return proto_timestamp


def to_proto_payload(message: Any) -> dict[str, Any]:
    return MessageToDict(
        message,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True,
    )
