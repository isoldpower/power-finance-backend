from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    """
    ISO 4217 currency definition.
    """

    code: str
    name: str
    numeric: str
    digits: int
