from enum import StrEnum
from uuid import UUID


class ReplyEvent(StrEnum):
    ACCEPTED = "accepted"
    DELTA = "delta"
    MESSAGE = "message"
    ERROR = "error"


def accepted_frame(user_message_id: UUID, message_id: UUID) -> dict:
    return _frame(
        ReplyEvent.ACCEPTED,
        {
            "user_message_id": str(user_message_id),
            "message_id": str(message_id),
        },
    )


def delta_frame(text: str) -> dict:
    return _frame(ReplyEvent.DELTA, {"text": text})


def message_frame(message: dict) -> dict:
    return _frame(ReplyEvent.MESSAGE, message)


def error_frame(code: str, message: str, message_id: UUID) -> dict:
    return _frame(
        ReplyEvent.ERROR,
        {
            "code": code,
            "message": message,
            "message_id": str(message_id),
        },
    )


def _frame(event: ReplyEvent, data: dict) -> dict:
    return {
        "event": str(event),
        "data": data,
    }
