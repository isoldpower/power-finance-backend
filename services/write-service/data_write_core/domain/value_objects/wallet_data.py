class WalletData:
    title: str
    currency_code: str

    def __init__(self, title: str, currency_code: str) -> None:
        self.title = title
        self.currency_code = currency_code
