from sqlalchemy import and_, or_
from sqlalchemy.sql.expression import case

from service_core.shared.db_connection import (
    CREDIT_NORMAL_GROUPS,
    DEBIT_NORMAL_GROUPS,
    AccountModel,
    EntryModel,
)


def signed_amount():
    debit_normal = AccountModel.group.in_(DEBIT_NORMAL_GROUPS)
    credit_normal = AccountModel.group.in_(CREDIT_NORMAL_GROUPS)

    raises_the_balance = or_(
        and_(debit_normal, EntryModel.debit.is_(True)),
        and_(credit_normal, EntryModel.debit.is_(False)),
    )

    return case(
        (raises_the_balance, EntryModel.book_amount),
        (or_(debit_normal, credit_normal), -EntryModel.book_amount),
        else_=0,
    )
