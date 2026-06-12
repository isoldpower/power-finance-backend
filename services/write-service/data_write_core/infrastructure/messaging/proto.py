from datetime import UTC, datetime
from uuid import uuid4

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message
from google.protobuf.timestamp_pb2 import Timestamp

from data_write_core.domain.value_objects import OutboxEntry

_DEFAULT_SCHEMA_VERSION = 1
# Partition key for events that don't belong to any user
GLOBAL_PARTITION_KEY = "GLOBAL"


def datetime_to_timestamp(value: datetime) -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(value)
    return timestamp


def build_outbox_entry(
    message: Message,
    *,
    aggregate_type: str,
    aggregate_id: str,
    partition_key: str,
) -> OutboxEntry:
    """Stamp envelope fields onto a kafka_messages proto and project it to an OutboxEntry.

    The partition key becomes the Kafka message key (Debezium routes the
    `partitionkey` column there). For user-scoped events it must be the
    user's external (Clerk) id so per-user consumers can match it against
    the gateway-authenticated identity; events without a user owner use
    GLOBAL_PARTITION_KEY.
    """

    event_id = uuid4()
    occurred_at = datetime.now(UTC)

    message.event_id = str(event_id)
    message.occurred_at.FromDatetime(occurred_at)
    if not message.schema_version:
        message.schema_version = _DEFAULT_SCHEMA_VERSION

    return OutboxEntry(
        event_id=event_id,
        event_type=message.DESCRIPTOR.name,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        partition_key=partition_key or GLOBAL_PARTITION_KEY,
        occurred_at=occurred_at,
        schema_version=message.schema_version,
        payload=MessageToDict(
            message,
            preserving_proto_field_name=True,
            always_print_fields_with_no_presence=True,
        ),
    )
