def get_single_wallet_key(wallet_id: str) -> str:
    return f"read:wallet:{wallet_id}"


def get_single_transaction_key(transaction_id: str) -> str:
    return f"read:transaction:{transaction_id}"
