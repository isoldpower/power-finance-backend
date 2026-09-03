"""The staleness reroute, from both ends.

read-service answers 507 when its projection is behind the caller's
`Read-At-Least`, and the `read-fallback` plugin re-issues the request against
write-service's always-consistent copy. The 507 is INTERNAL — the target
correctly says no error code covers this case, so a client must never see one.

That only holds where a fallback route actually exists. The plugin re-issues
every GET by rewriting the prefix, so a read with no counterpart on the write
side does not leak the 507 — it produces write-service's 404 instead, which is
worse: a resource that exists reported as missing.
"""

import re
from functools import cache

from .documents import API_PREFIX, REPOSITORY, normalise

READ_VIEWS = REPOSITORY / "services" / "read-service" / "data_read_core" / "query_slices"
WRITE_URLS = (
    REPOSITORY
    / "services"
    / "write-service"
    / "data_write_core"
    / "presentation"
    / "http"
    / "urls.py"
)

FALLBACK_PREFIX = "fallback-reads"

_GATE = re.compile(r"@(es_)?read_at_least_gate")
_ROUTE = re.compile(r'^\s*"([^"]+)",\s*$', re.MULTILINE)
_DJANGO_PARAMETER = re.compile(r"<[^>]+>")


@cache
def gated_read_slices() -> frozenset[str]:
    """Every read-service slice whose view is behind a Read-At-Least gate, and
    which can therefore answer 507."""

    gated = set()
    for view in READ_VIEWS.glob("*/http/view.py"):
        if _GATE.search(view.read_text(encoding="utf-8")):
            gated.add(view.parents[1].name)

    return frozenset(gated)


@cache
def gated_read_paths() -> frozenset[str]:
    """The URL patterns those slices are mounted at."""

    urls = (READ_VIEWS / "urls.py").read_text(encoding="utf-8")
    mounted = re.findall(r'path\(\s*"([^"]*)"\s*,\s*(\w+)', urls)

    return frozenset(
        normalise("/" + _DJANGO_PARAMETER.sub("{}", path))
        for path, handler in mounted
        if handler in gated_read_slices()
    )


@cache
def fallback_paths() -> frozenset[str]:
    """The write-side counterparts, with the fallback prefix stripped so the two
    sets compare directly."""

    declared = _ROUTE.findall(WRITE_URLS.read_text(encoding="utf-8"))

    return frozenset(
        normalise("/" + _DJANGO_PARAMETER.sub("{}", route).removeprefix(f"{FALLBACK_PREFIX}/"))
        for route in declared
        if route.startswith(f"{FALLBACK_PREFIX}/")
    )


def fallback_route_for(path: str) -> str:
    """What the plugin rewrites a read path to."""

    return f"{API_PREFIX}/{FALLBACK_PREFIX}{normalise(path)}"
