import asyncio

from asgiref.sync import async_to_sync
from celery import shared_task
from celery.utils.log import get_task_logger

from finances.application.bootstrap import get_repository_registry
from finances.domain.builders import WalletBuilder
from finances.domain.entities import BalanceCheckpoint

logger = get_task_logger(__name__)


@shared_task(name="finances.checkpoint_wallet_balances")
def checkpoint_wallet_balances() -> None:
    async_to_sync(_checkpoint_wallet_balances)()


async def _checkpoint_wallet_balances() -> None:
    logger.info("Task [finances.checkpoint_wallet_balances]: Starting balance checkpoint")

    try:
        registry = get_repository_registry()
        all_wallets = await registry.wallet_repository.get_all_active_wallets()

        logger.info("Task [finances.checkpoint_wallet_balances]: Checkpointing %d wallets", len(all_wallets))
        checkpoints = await asyncio.gather(*[
            registry.transaction_repository.get_checkpoint(wallet.id)
            for wallet in all_wallets
        ])
        wallet_transactions = await asyncio.gather(*[
            registry.transaction_repository.get_unsettled_transactions(
                wallet.id, checkpoint.settled_at if checkpoint else None
            )
            for wallet, checkpoint in zip(all_wallets, checkpoints)
        ])
        for wallet, checkpoint, transactions in zip(all_wallets, checkpoints, wallet_transactions):
            wallet = (
                WalletBuilder(wallet)
                    .set_checkpoint(checkpoint)
                    .set_transactions(transactions)
                    .build_wallet()
            )
            await registry.transaction_repository.save_checkpoint(
                BalanceCheckpoint.create(wallet)
            )

        logger.info("Task [finances.checkpoint_wallet_balances]: Completed successfully")
    except Exception as exc:
        logger.error("Task [finances.checkpoint_wallet_balances]: Error - %s", str(exc))
