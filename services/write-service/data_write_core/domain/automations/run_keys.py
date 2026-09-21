from datetime import datetime
from uuid import UUID

from .vocabulary import TriggerSchedule

RUN_KEY_MAX_LENGTH = 128


def transaction_run_key(transaction_id: UUID | str) -> str:
    return f"transaction:{transaction_id}"


def wallet_run_key(wallet_id: UUID | str, schedule: str, moment: datetime) -> str:
    return f"wallet:{wallet_id}@{period_bucket(schedule, moment)}"


def period_bucket(schedule: str, moment: datetime) -> str:
    if schedule == TriggerSchedule.WEEKLY:
        iso_year, iso_week, _ = moment.isocalendar()

        return f"{iso_year:04d}-W{iso_week:02d}"

    if schedule == TriggerSchedule.MONTHLY:
        return f"{moment.year:04d}-{moment.month:02d}"

    return moment.date().isoformat()
