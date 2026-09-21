from sqlalchemy import and_, or_
from sqlalchemy.sql.expression import case

from service_core.shared.db_connection import (
    AccountGroup,
    AccountModel,
    EntryModel,
)


def signed_amount():
    debit_normal = AccountModel.group.in_(AccountGroup.debit_normal())
    credit_normal = AccountModel.group.in_(AccountGroup.credit_normal())

    raises_the_balance = or_(
        and_(debit_normal, EntryModel.debit.is_(True)),
        and_(credit_normal, EntryModel.debit.is_(False)),
    )

    return case(
        (raises_the_balance, EntryModel.book_amount),
        (or_(debit_normal, credit_normal), -EntryModel.book_amount),
        else_=0,
    )
