def _format_context(context: dict[str, object]) -> str:
    if not context:
        return ""
    pairs = ", ".join(f"{key}={value}" for key, value in context.items())
    return f" ({pairs})"
