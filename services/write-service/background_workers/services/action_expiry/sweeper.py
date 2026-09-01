import asyncio
import logging

from data_write_core.application.commands import (
    ExpireLapsedActionsCommand,
    ExpireLapsedActionsCommandHandler,
)

from .config import ActionExpirySettings

logger = logging.getLogger("background_workers.action_expiry")


async def run_expiry_sweeps(
    settings: ActionExpirySettings,
    stop_signal: asyncio.Event | None = None,
) -> None:
    stop_signal = stop_signal or asyncio.Event()
    logger.info(
        "action_expiry: sweeping every %ss, up to %s actions per run",
        settings.interval_seconds,
        settings.batch_limit,
    )

    while not stop_signal.is_set():
        await sweep_once(settings)
        with_suppressed_timeout = asyncio.wait_for(
            stop_signal.wait(),
            timeout=settings.interval_seconds,
        )
        try:
            await with_suppressed_timeout
        except TimeoutError:
            continue


async def sweep_once(settings: ActionExpirySettings) -> list[str]:
    try:
        expired_actions = await ExpireLapsedActionsCommandHandler().handle(
            ExpireLapsedActionsCommand(limit=settings.batch_limit)
        )
    except Exception:
        logger.exception("action_expiry: sweep failed; retrying next interval")

        return []

    if expired_actions:
        logger.info(
            "action_expiry: expired %d action(s)",
            len(expired_actions),
        )

    return expired_actions
