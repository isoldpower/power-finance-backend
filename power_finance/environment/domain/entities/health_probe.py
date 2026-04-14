from enum import Enum


class HealthProbeStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
