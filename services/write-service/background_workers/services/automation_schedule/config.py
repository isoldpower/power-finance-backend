from dataclasses import dataclass

from django.conf import settings

DEFAULT_INTERVAL_SECONDS = 300


@dataclass(frozen=True)
class AutomationScheduleSettings:
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS


def get_automation_schedule_settings() -> AutomationScheduleSettings:
    configured = getattr(settings, "AUTOMATION_SCHEDULE", {})

    return AutomationScheduleSettings(
        interval_seconds=int(
            configured.get(
                "INTERVAL_SECONDS",
                DEFAULT_INTERVAL_SECONDS,
            )
        ),
    )
