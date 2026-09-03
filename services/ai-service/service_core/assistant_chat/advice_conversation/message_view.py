from service_core.shared.timestamps import to_iso

from .contracts import ConversationMessage


def present_message(message: ConversationMessage) -> dict:
    return {
        "id": str(message.id),
        "created_at": to_iso(message.created_at),
        "role": str(message.role),
        "status": str(message.status),
        "text": message.text,
        "refs": [reference.as_dict() for reference in message.refs],
    }


def present_messages(messages: list[ConversationMessage]) -> list[dict]:
    return [present_message(message) for message in messages]
