from secrets import token_hex

DEMO_EXTERNAL_ID_PREFIX = "demo_"
DEMO_EXTERNAL_ID_RANDOM_BYTES = 16


def new_demo_external_id() -> str:
    return f"{DEMO_EXTERNAL_ID_PREFIX}{token_hex(DEMO_EXTERNAL_ID_RANDOM_BYTES)}"


def is_demo_external_id(external_id: str) -> bool:
    return external_id.startswith(DEMO_EXTERNAL_ID_PREFIX) and len(external_id) > len(
        DEMO_EXTERNAL_ID_PREFIX
    )
