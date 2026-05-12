from dataclasses import dataclass


@dataclass(frozen=True)
class ExpenditureAnalyticsResultDTO:
    expenditure_by_month: dict[str, dict[str, float]]