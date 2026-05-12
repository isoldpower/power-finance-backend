from enum import Enum


class ProbeStatus(str, Enum):
    """Coarse result of a single dependency check. Carried by every health
    report; `ok` means the dependency is reachable and behaving, `degraded`
    means anything else (timeout, auth error, unexpected response)."""

    OK = "ok"
    DEGRADED = "degraded"
