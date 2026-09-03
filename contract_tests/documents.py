"""The three documents this suite holds the implementation against.

Parsed rather than restated: a target endpoint that stops being listed should
stop being required, and a deviation that stops being documented should start
failing.
"""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]

TARGET = REPOSITORY / "API_TARGET.md"
DIFF = REPOSITORY / "API_DIFF.md"
KONG_CONFIG = REPOSITORY / "infrastructure" / "kong" / "kong.yml"

API_PREFIX = "/api/v1"
METHODS = ("GET", "POST", "PATCH", "PUT", "DELETE")

_ENDPOINT_HEADING = re.compile(rf"^### ({'|'.join(METHODS)}) (/\S+)$")
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


def key(endpoint: Endpoint) -> tuple[str, str]:
    return (endpoint.method, normalise(endpoint.path))


@cache
def target_endpoints() -> tuple[Endpoint, ...]:
    """Every endpoint API_TARGET.md gives its own `### METHOD /path` heading."""

    found = []
    for line in TARGET.read_text(encoding="utf-8").splitlines():
        heading = _ENDPOINT_HEADING.match(line)
        if heading:
            found.append(Endpoint(method=heading.group(1), path=heading.group(2)))

    return tuple(found)


@cache
def diff_document() -> str:
    return DIFF.read_text(encoding="utf-8")


def is_documented_deviation(endpoint: Endpoint) -> bool:
    """A path that appears in API_DIFF.md has been explained to the frontend.

    Deliberately a substring check on the path rather than anything cleverer:
    the point is that a client reading the diff would find it, and a client
    does not run a parser.
    """

    return normalise(endpoint.path) in _normalised_diff_paths()


@cache
def _normalised_diff_paths() -> frozenset[str]:
    quoted = re.findall(r"`([A-Z]+ )?(/[A-Za-z0-9_\-{}/]+)`", diff_document())

    return frozenset(normalise(path) for _, path in quoted)
