from dataclasses import dataclass

from django.conf import settings

# Far shorter than `daily` means, on purpose. The sweeper does not decide WHEN a
# rule is due — the period is part of the run key, so a rule that already ran
# this period is refused its claim. Waking often therefore costs a query and
# buys a short catch-up after an outage.
DEFAULT_INTERVAL_SECONDS = 300


@dataclass(frozen=True)
class AutomationScheduleSettings:
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS


def get_automation_schedule_settings() -> AutomationScheduleSettings:
    configured = getattr(settings, "AUTOMATION_SCHEDULE", {})

    return AutomationScheduleSettings(
        interval_seconds=int(configured.get("INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)),
    )
