from ..contracts import Overview


def present_overview(overview: Overview) -> dict:
    return {
        "signals": [signal.as_dict() for signal in overview.signals],
        "prompts": list(overview.prompts),
    }
