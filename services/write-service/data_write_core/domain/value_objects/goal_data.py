from datetime import datetime
from decimal import Decimal


class GoalData:
    title: str
    currency_code: str
    target: Decimal
    finish_at: datetime | None
    url: str | None

    def __init__(
        self,
        title: str,
        currency_code: str,
        target: Decimal,
        finish_at: datetime | None = None,
        url: str | None = None,
    ) -> None:
        self.title = title
        self.currency_code = currency_code
        self.target = target
        self.finish_at = finish_at
        self.url = url
