from decimal import Decimal

from .category import CategoryReference


class WalletData:
    title: str
    currency_code: str
    category: CategoryReference | None
    color: str
    favorite: bool
    zero_balance: Decimal

    def __init__(
        self,
        title: str,
        currency_code: str,
        category: CategoryReference | None = None,
        color: str = "",
        favorite: bool = False,
        zero_balance: Decimal = Decimal("0"),
    ) -> None:
        self.title = title
        self.currency_code = currency_code
        self.category = category
        self.color = color
        self.favorite = favorite
        self.zero_balance = zero_balance
