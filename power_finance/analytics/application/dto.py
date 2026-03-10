from dataclasses import dataclass


@dataclass (frozen=True)
class MoneyFlowNodeDTO:
    id: int
    name: str
    level: int

@dataclass (frozen=True)
class MoneyFlowLinkDTO:
    source_id: int
    target_id: int
    value: float

@dataclass (frozen=True)
class MoneyFlowResultDTO:
    nodes: list[MoneyFlowNodeDTO]
    links: list[MoneyFlowLinkDTO]