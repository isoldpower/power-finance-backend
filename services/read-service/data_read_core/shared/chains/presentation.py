from collections.abc import Mapping


def present_chain(chain_id: str | None, chain_sizes: Mapping[str, int]) -> dict | None:
    if not chain_id:
        return None

    return {
        "id": chain_id,
        "size": chain_sizes.get(chain_id, 0),
    }
