from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RateSnapshotDTO:
    base: str
    rates: dict[str, Decimal]
    fetched_at: datetime
