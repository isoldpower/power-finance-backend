from enum import Enum


class ProbeStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
