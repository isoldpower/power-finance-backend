from finances.domain.entities import Transaction, Wallet

from .dtos import WalletDTO, TransactionDTO, TransactionParticipantDTO, TransactionPlainDTO, \
    TransactionParticipantPlainDTO


def wallet_to_dto(wallet: Wallet) -> WalletDTO:
    return WalletDTO(
        id=wallet.id,
        user_id=wallet.user_id,
        name=wallet.name,
        balance_amount=wallet.balance.amount,
        currency=wallet.balance.currency_code,
        credit=wallet.credit,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )

def transaction_to_dto(
    transaction: Transaction,
    sender_wallet: Wallet | None = None,
    receiver_wallet: Wallet | None = None,
) -> TransactionDTO:
    return TransactionDTO(
        id=transaction.id,
        sender=TransactionParticipantDTO(
            wallet=wallet_to_dto(sender_wallet),
            amount=transaction.sender.amount,
        ) if transaction.sender and sender_wallet else None,
        receiver=TransactionParticipantDTO(
            wallet=wallet_to_dto(receiver_wallet),
            amount=transaction.receiver.amount,
        ) if transaction.receiver and receiver_wallet else None,
        description=transaction.description,
        created_at=transaction.created_at,
        type=transaction.type,
        category=transaction.category,
    )

def transaction_to_plain_dto(
    transaction: Transaction,
) -> TransactionPlainDTO:
    return TransactionPlainDTO(
        id=transaction.id,
        sender=TransactionParticipantPlainDTO(
            wallet_id=transaction.sender.wallet_id,
            amount=transaction.sender.amount,
        ) if transaction.sender else None,
        receiver=TransactionParticipantPlainDTO(
            wallet_id=transaction.receiver.wallet_id,
            amount=transaction.receiver.amount,
        ) if transaction.receiver else None,
        description=transaction.description,
        created_at=transaction.created_at,
        type=transaction.type,
        category=transaction.category,
    )