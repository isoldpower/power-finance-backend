from finances.domain.entities.balance_checkpoint import BalanceCheckpoint
from finances.domain.entities.transaction import Transaction
from finances.domain.entities.wallet import Wallet


class WalletBuilder:
    def __init__(self, wallet: Wallet):
        self._wallet = wallet
        self._transactions_set = False
        self._checkpoint_set = False

    def set_transactions(self, transactions: list[Transaction]) -> 'WalletBuilder':
        self._wallet.unsettled_transactions = transactions
        self._transactions_set = True
        return self

    def set_checkpoint(self, checkpoint: BalanceCheckpoint | None) -> 'WalletBuilder':
        self._wallet.checkpoint = checkpoint
        self._checkpoint_set = True
        return self

    def build_wallet(self) -> Wallet:
        if not self._transactions_set or not self._checkpoint_set:
            raise RuntimeError('WalletBuilder: set_transactions and set_checkpoint must both be called before build_wallet')
        return self._wallet
