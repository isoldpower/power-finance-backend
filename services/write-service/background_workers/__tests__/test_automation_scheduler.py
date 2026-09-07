from datetime import UTC, datetime

from data_write_core.domain.automations import TriggerSchedule

from background_workers.services.automation_schedule import (
    AutomationScheduleSettings,
    sweep_once,
)

NOW = datetime(2026, 9, 1, tzinfo=UTC)


class FakeEngine:
    def __init__(self, failing: str = "") -> None:
        self.swept: list[str] = []
        self.failing = failing

    async def run_scheduled(self, schedule: str, now: datetime) -> list[str]:
        self.swept.append(schedule)
        if schedule == self.failing:
            raise RuntimeError("sweep failed")

        return [f"{schedule}-rule"]


async def test_every_schedule_is_swept_on_every_pass():
    engine = FakeEngine()

    await sweep_once(NOW, engine)

    assert engine.swept == [member.value for member in TriggerSchedule]


async def test_one_schedule_failing_does_not_cost_the_others_their_period():
    engine = FakeEngine(failing=TriggerSchedule.WEEKLY)

    applied = await sweep_once(NOW, engine)

    assert applied == ["daily-rule", "monthly-rule"]


def test_the_sweeper_wakes_far_more_often_than_daily_means():
    assert AutomationScheduleSettings().interval_seconds <= 3600
