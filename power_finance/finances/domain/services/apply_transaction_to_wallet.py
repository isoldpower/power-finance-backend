from ..entities import Transaction, Wallet
from ..value_objects import Money


def apply_transaction_to_wallet_balance(
    transaction: Transaction,
    sender_wallet: Wallet | None = None,
    receiver_wallet: Wallet | None = None,
):
    if sender_wallet and transaction.sender:
        sender_wallet.withdraw_money(Money(
            amount=transaction.sender.amount,
            currency_code=sender_wallet.balance.currency_code
        ))

    if receiver_wallet and transaction.receiver:
        receiver_wallet.deposit_money(Money(
            amount=transaction.receiver.amount,
            currency_code=receiver_wallet.balance.currency_code
        ))


def rollback_transaction_from_wallet_balance(
    transaction: Transaction,
    sender_wallet: Wallet | None = None,
    receiver_wallet: Wallet | None = None,
):
    if sender_wallet and transaction.sender:
        sender_wallet.deposit_money(Money(
            amount=transaction.sender.amount,
            currency_code=sender_wallet.balance.currency_code
        ))

    if receiver_wallet and transaction.receiver:
        receiver_wallet.withdraw_money(Money(
            amount=transaction.receiver.amount,
            currency_code=receiver_wallet.balance.currency_code
        ))
