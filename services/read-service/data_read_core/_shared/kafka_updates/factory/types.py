from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ConsumerConfig:
    bootstrap_servers: str
    group_id: str
    topics: Sequence[str]
    auto_offset_reset: str = "earliest"
    session_timeout_ms: int = 45_000
    max_poll_interval_ms: int = 300_000
    isolation_level: str = "read_committed"
    poll_timeout_ms: int = 1_000
    extra: dict[str, object] = field(default_factory=dict)
