def apply_transaction_to_wallet_balance(*args, **kwargs):
    raise NotImplementedError("Balance is computed from transaction ledger — wallet mutation is no longer supported")


def rollback_transaction_from_wallet_balance(*args, **kwargs):
    raise NotImplementedError("Balance is computed from transaction ledger — wallet mutation is no longer supported")
