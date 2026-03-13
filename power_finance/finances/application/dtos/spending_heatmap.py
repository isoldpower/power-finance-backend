from dataclasses import dataclass


@dataclass(frozen=True)
class SpendingHeatmapResultDTO:
    spending_by_day: dict[str, float]