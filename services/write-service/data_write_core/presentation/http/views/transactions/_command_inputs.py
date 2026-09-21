from data_write_core.domain.value_objects import TransactionOrigin, TransactionType


def evidence_url_of(validated: dict) -> str | None:
    evidence = validated.get("evidence")

    return evidence["url"] if evidence else None


def transaction_type_of(validated: dict) -> TransactionType:
    return TransactionType(validated["type"])


def origin_of(validated: dict) -> TransactionOrigin:
    return TransactionOrigin(validated.get("origin", TransactionOrigin.MANUAL.value))
