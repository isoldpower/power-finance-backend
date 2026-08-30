from decimal import Decimal


def money(amount: Decimal) -> str:
    """Decimals travel as strings, so no consumer parses them as a float."""

    return str(amount)
