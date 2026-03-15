from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryAnalyticsItemDTO:
    category: str
    amount: float

@dataclass(frozen=True)
class CategoryAnalyticsResultDTO:
    items: list[CategoryAnalyticsItemDTO]