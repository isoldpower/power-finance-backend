from typing import NamedTuple


class QuotaDecisionDTO(NamedTuple):
    granted: bool
    allowance: int
    consumed: int
