from opentelemetry import baggage
from opentelemetry.context import Context


def read_baggage_entry(entry_name: str, context: Context | None = None) -> str | None:
    entry_value = baggage.get_baggage(entry_name, context)
    if entry_value is None:
        return None

    return str(entry_value)


def write_baggage_entry(
    entry_name: str,
    entry_value: str,
    context: Context | None = None,
) -> Context:
    return baggage.set_baggage(
        entry_name,
        entry_value,
        context,
    )
