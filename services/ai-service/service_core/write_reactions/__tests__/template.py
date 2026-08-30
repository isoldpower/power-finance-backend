"""The chart of accounts these tests drive the reactions with.

`background_workers` holds the one the service actually runs on; this is
service_core's own copy, because a chunk's tests may not reach into the wiring
layer to find out what it will be handed. The two have to agree — `user_created`
seeds the accounts `transaction_created` later resolves — so
`background_workers` has a test asserting its chart matches this one. That
assertion lives there because the wiring layer is allowed to import service_core
and not the other way round.
"""

from ..transaction_created import (
    AccountSpec as CreatedAccountSpec,
)
from ..transaction_created import (
    PostingDispatcher as CreatedDispatcher,
)
from ..transaction_created import (
    TemplateAccount as CreatedTemplateAccount,
)
from ..transaction_created import (
    TemplateDispatcher as CreatedTemplateDispatcher,
)
from ..transaction_updated import (
    AccountSpec as UpdatedAccountSpec,
)
from ..transaction_updated import (
    PostingDispatcher as UpdatedDispatcher,
)
from ..transaction_updated import (
    TemplateAccount as UpdatedTemplateAccount,
)
from ..transaction_updated import (
    TemplateDispatcher as UpdatedTemplateDispatcher,
)
from ..user_created import (
    AccountSpec as SeedAccountSpec,
)
from ..user_created import (
    TemplateAccount as SeedTemplateAccount,
)

TEMPLATE: tuple[tuple[str, str, bool], ...] = (
    ("liabilities", "temporary-liability", True),
    ("assets", "temporary-assets", False),
)

SEED_TEMPLATE_ACCOUNTS = tuple(
    SeedTemplateAccount(SeedAccountSpec(group=group, name=name), debit=debit)
    for group, name, debit in TEMPLATE
)

CREATED_TEMPLATE_ACCOUNTS = tuple(
    CreatedTemplateAccount(CreatedAccountSpec(group=group, name=name), debit=debit)
    for group, name, debit in TEMPLATE
)

UPDATED_TEMPLATE_ACCOUNTS = tuple(
    UpdatedTemplateAccount(UpdatedAccountSpec(group=group, name=name), debit=debit)
    for group, name, debit in TEMPLATE
)


def build_created_dispatcher(accounts) -> CreatedDispatcher:
    return CreatedTemplateDispatcher(accounts, CREATED_TEMPLATE_ACCOUNTS)


def build_updated_dispatcher(accounts) -> UpdatedDispatcher:
    return UpdatedTemplateDispatcher(accounts, UPDATED_TEMPLATE_ACCOUNTS)
