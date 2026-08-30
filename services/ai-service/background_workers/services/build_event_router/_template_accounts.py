from service_core.write_reactions import transaction_created, transaction_updated, user_created

_TEMPLATE: tuple[tuple[str, str, bool], ...] = (
    ("liabilities", "temporary-liability", True),
    ("assets", "temporary-assets", False),
)

SEED_TEMPLATE_ACCOUNTS: tuple[user_created.TemplateAccount, ...] = tuple(
    user_created.TemplateAccount(
        user_created.AccountSpec(group=group, name=name),
        debit=debit,
    )
    for group, name, debit in _TEMPLATE
)

CREATED_TEMPLATE_ACCOUNTS: tuple[transaction_created.TemplateAccount, ...] = tuple(
    transaction_created.TemplateAccount(
        transaction_created.AccountSpec(group=group, name=name),
        debit=debit,
    )
    for group, name, debit in _TEMPLATE
)

UPDATED_TEMPLATE_ACCOUNTS: tuple[transaction_updated.TemplateAccount, ...] = tuple(
    transaction_updated.TemplateAccount(
        transaction_updated.AccountSpec(group=group, name=name),
        debit=debit,
    )
    for group, name, debit in _TEMPLATE
)


def build_created_dispatcher(
    accounts: transaction_created.AccountRepository,
) -> transaction_created.PostingDispatcher:
    return transaction_created.TemplateDispatcher(
        accounts,
        CREATED_TEMPLATE_ACCOUNTS,
    )


def build_updated_dispatcher(
    accounts: transaction_updated.AccountRepository,
) -> transaction_updated.PostingDispatcher:
    return transaction_updated.TemplateDispatcher(
        accounts,
        UPDATED_TEMPLATE_ACCOUNTS,
    )
