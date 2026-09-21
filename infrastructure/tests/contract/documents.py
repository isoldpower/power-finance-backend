"""Paths and spellings shared by the readers this suite is built from."""

import re
from dataclasses import dataclass
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]

KONG_CONFIG = REPOSITORY / "infrastructure" / "kong" / "kong.yml"

API_PREFIX = "/api/v1"
METHODS = ("GET", "POST", "PATCH", "PUT", "DELETE")

_PARAMETER = re.compile(r"\{[^}]+\}")


@dataclass(frozen=True, slots=True)
class Endpoint:
    method: str
    path: str

    def __str__(self) -> str:
        return f"{self.method} {self.path}"


def normalise(path: str) -> str:
    """Two spellings of one route compare equal.

    The documents write `{wallet-id}`, Django writes `{wallet_id}` and the
    target omits the version prefix the services mount under. None of that is a
    difference in the surface.
    """

    without_prefix = path[len(API_PREFIX) :] if path.startswith(API_PREFIX) else path

    return _PARAMETER.sub("{}", without_prefix)
