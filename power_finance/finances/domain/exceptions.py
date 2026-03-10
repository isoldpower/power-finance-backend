class UnsupportedCurrencyError(Exception):
    """Raised when the currency that was requested does not exist or is not supported"""

    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code

        super().__init__(f"Unsupported currency code '{currency_code}' encountered.")
