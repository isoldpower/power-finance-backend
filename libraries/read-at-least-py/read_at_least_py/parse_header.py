def parse_read_at_least(raw_value: str | None) -> int | None:
    """Parse a Read-At-Least header value into an outbox seq."""

    if raw_value is None:
        return None

    return _safe_parse(raw_value)


def _safe_parse(raw: str) -> int | None:
    sequence_candidate = raw.strip().split(":", 1)[0]
    if not sequence_candidate:
        return None

    try:
        sequence = int(sequence_candidate)
    except ValueError:
        return None

    return sequence if sequence > 0 else None
