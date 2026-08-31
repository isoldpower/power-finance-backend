from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectionContext:
    path: str
    external_id: str
