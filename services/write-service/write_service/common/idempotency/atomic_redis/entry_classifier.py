from typing import Any

from .entry_codec import STATE_COMPLETED
from .outcomes import (
    AcquireResult,
    AlreadyCompleted,
    InProgress,
    Mismatch,
    StoredResponse,
)


class EntryClassifier:
    @staticmethod
    def classify(
        existing_entry: dict[str, Any] | None,
        request_hash: str,
    ) -> AcquireResult:
        if existing_entry is None:
            return InProgress()

        stored_hash = existing_entry.get("request_hash", "")
        if stored_hash and stored_hash != request_hash:
            return Mismatch(stored_hash=stored_hash)

        if existing_entry.get("state") == STATE_COMPLETED:
            return AlreadyCompleted(
                response=StoredResponse(
                    status_code=int(existing_entry["status_code"]),
                    body=existing_entry.get("body"),
                    headers=existing_entry.get("headers", {}),
                    request_hash=stored_hash,
                )
            )

        return InProgress()


__all__ = ["EntryClassifier"]
