import json


def format_payload(data: dict, lines: list[str]) -> list[str]:
    lines_copy = lines.copy()
    payload = json.dumps(data, ensure_ascii=False)
    for line in payload.splitlines():
        lines_copy.append(f"data: {line}")

    lines_copy.append("")
    lines_copy.append("")

    return lines_copy

def format_sse(
        data: dict,
        event: str,
        event_id: str,
) -> str:
    header_lines: list[str] = [f"event: {event}", f"id: {event_id}"]
    total_lines = format_payload(data, header_lines)

    return "\n".join(total_lines)
