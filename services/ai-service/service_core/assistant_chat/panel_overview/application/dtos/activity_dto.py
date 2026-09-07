from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ConversationActivityDTO:
    spend_currency: str
    spend_this_month: Decimal
    spend_last_month: Decimal
    uncategorised: int
    recorded_this_month: int
