from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ConversationActivity:
    """The few numbers the signals are derived from.

    Spend is reported in ONE currency — the one the user transacts in most —
    because a percentage across mixed currencies would either need today's
    exchange rate inside a cached read or would be quietly wrong.
    """

    spend_currency: str
    spend_this_month: Decimal
    spend_last_month: Decimal
    uncategorised: int
    recorded_this_month: int
