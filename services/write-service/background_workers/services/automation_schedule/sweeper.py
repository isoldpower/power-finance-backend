import asyncio
import logging
from datetime import UTC, datetime

from data_write_core.application.commands.automations.engine import (
    EFFECT_EXECUTORS,
    AutomationEngine,
)
from data_write_core.domain.automations import TriggerSchedule

from .config import AutomationScheduleSettings

logger = logging.getLogger("background_workers.automation_schedule")


async def run_schedule_sweeps(
    settings: AutomationScheduleSettings,
    stop_signal: asyncio.Event | None = None,
) -> None:
    stop_signal = stop_signal or asyncio.Event()
    logger.info(
        "automation_schedule: sweeping every %ss",
        settings.interval_seconds,
    )

    while not stop_signal.is_set():
        await sweep_once()
        try:
            await asyncio.wait_for(
                stop_signal.wait(),
                timeout=settings.interval_seconds,
            )
        except TimeoutError:
            continue


async def sweep_once(
    now: datetime | None = None,
    engine: AutomationEngine | None = None,
) -> list[str]:
    timestamp_now = now or datetime.now(UTC)
    engine = engine or AutomationEngine(EFFECT_EXECUTORS)
    applied_automations: list[str] = []

    for schedule in TriggerSchedule:
        try:
            applied_automations.extend(await engine.run_scheduled(schedule, timestamp_now))
        except Exception:
            logger.exception(
                "automation_schedule: %s sweep failed; retrying next pass",
                schedule,
            )

    if applied_automations:
        logger.info(
            "automation_schedule: %d rule run(s) applied",
            len(applied_automations),
        )

    return applied_automations
