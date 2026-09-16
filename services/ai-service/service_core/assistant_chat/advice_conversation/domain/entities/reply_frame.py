from enum import StrEnum
from uuid import UUID


class ReplyEvent(StrEnum):
    ACCEPTED = "accepted"
    DELTA = "delta"
    MESSAGE = "message"
    ERROR = "error"


def accepted_frame(user_message_id: UUID, message_id: UUID, quota: dict | None = None) -> dict:
    return _frame(
        ReplyEvent.ACCEPTED,
        {
            "user_message_id": str(user_message_id),
            "message_id": str(message_id),
        },
        quota,
    )


def delta_frame(text: str) -> dict:
    return _frame(ReplyEvent.DELTA, {"text": text})


def message_frame(message: dict, quota: dict | None = None) -> dict:
    return _frame(ReplyEvent.MESSAGE, message, quota)


def error_frame(
    code: str,
    message: str,
    message_id: UUID | None,
    quota: dict | None = None,
) -> dict:
    return _frame(
        ReplyEvent.ERROR,
        {
            "code": code,
            "message": message,
            "message_id": str(message_id) if message_id is not None else None,
        },
        quota,
    )


# Quota rides beside the payload rather than inside it: what is left to spend
# belongs to the connection, not to the message being sent. Deltas carry none —
# nothing about an allowance changes mid-stream, and they are the frequent frame.
def _frame(event: ReplyEvent, data: dict, quota: dict | None = None) -> dict:
    frame = {
        "event": str(event),
        "data": data,
    }
    if quota is not None:
        frame["quota"] = quota

    return frame
