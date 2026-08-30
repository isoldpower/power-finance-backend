from sqlalchemy.orm import DeclarativeBase

ACCOUNT_GROUPS = ("assets", "liabilities", "equity")
DEBIT_NORMAL_GROUPS = ("assets",)
CREDIT_NORMAL_GROUPS = (
    "liabilities",
    "equity",
)


class ModelBase(DeclarativeBase):
    pass
