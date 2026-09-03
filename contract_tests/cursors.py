"""One opaque cursor, four implementations.

read-service, write-service and ai-service each keep their own codec — the
house pattern — and webhook-service reimplements it in Go. A client stores one
token whichever service answered it, so the four have to agree byte for byte,
and nothing but this holds them together.
"""

import json
import subprocess
from functools import cache

from .documents import REPOSITORY

# A fixed token, written down rather than generated: a round trip through one
# codec would pass even if all four drifted together.
GOLDEN_VALUES = ["2026-08-12T12:00:00+00:00", "7c3e9a10-4d2b-4f77-91cc-5e8b0a2f6d34"]
GOLDEN_ORDER = "created_at:desc,id:desc"
GOLDEN_DIRECTION = "next"

GO_CURSOR_PACKAGE = (
    REPOSITORY
    / "services"
    / "webhook-service"
    / "webhook_service"
    / "presentation"
    / "http"
    / "contract"
)

_SCRIPTS = {
    "read-service": (
        "import json;"
        "from data_read_core.shared.pagination.cursors.cursor_codec import CURSOR_CODEC;"
        "from data_read_core.shared.pagination.cursors.page_direction import PageDirection;"
        "from data_read_core.shared.pagination.cursors.query_fingerprint import "
        "query_fingerprint;"
        "from data_read_core.shared.pagination import CREATED_AT_DESC;"
        "fingerprint = query_fingerprint(CREATED_AT_DESC);"
        "print(json.dumps({{"
        "'order': CREATED_AT_DESC.signature,"
        "'fingerprint': fingerprint,"
        "'token': CURSOR_CODEC.encode(PageDirection.NEXT, {values}, fingerprint)}}))"
    ),
    "write-service": (
        "import json;"
        "from write_service.common.pagination import CREATED_AT_DESC;"
        "from write_service.common.pagination.cursors.cursor_codec import CURSOR_CODEC;"
        "from write_service.common.pagination.cursors.page_direction import PageDirection;"
        "from write_service.common.pagination.cursors.query_fingerprint import "
        "query_fingerprint;"
        "fingerprint = query_fingerprint(CREATED_AT_DESC);"
        "print(json.dumps({{"
        "'order': CREATED_AT_DESC.signature,"
        "'fingerprint': fingerprint,"
        "'token': CURSOR_CODEC.encode(PageDirection.NEXT, {values}, fingerprint)}}))"
    ),
    "ai-service": (
        "import json;"
        "from service_core.shared.pagination import ("
        "MESSAGE_FEED_ORDER, PageDirection, encode_cursor, query_fingerprint);"
        "fingerprint = query_fingerprint(MESSAGE_FEED_ORDER);"
        "print(json.dumps({{"
        "'order': MESSAGE_FEED_ORDER,"
        "'fingerprint': fingerprint,"
        "'token': encode_cursor(PageDirection.NEXT, tuple({values}), fingerprint)}}))"
    ),
}


@cache
def minted() -> dict[str, dict]:
    """What each Python service produces for the golden position."""

    results = {}
    for service, script in _SCRIPTS.items():
        completed = subprocess.run(
            ("uv", "run", "python", "-c", script.format(values=repr(GOLDEN_VALUES))),
            cwd=REPOSITORY / "services" / service,
            capture_output=True,
            text=True,
            check=True,
        )
        results[service] = json.loads(completed.stdout[completed.stdout.index("{") :])

    return results


# A cursor is bound to the query that produced it by a fingerprint over the
# sort order AND the active filters. read-service mints one; when the projection
# goes stale the gateway hands the very same token to write-service, which
# rebuilds the fingerprint from its own copy of the filter material. If the two
# dicts differ by so much as a key name the token is rejected as a mismatch, and
# the client loses the page it could already see.
_FILTER_MATERIAL_SCRIPTS = {
    "read-service": (
        "import json;"
        "from data_read_core.query_slices.list_actions.dtos import ActionFilters;"
        "from data_read_core.query_slices.list_automations.dtos import AutomationFilters;"
        "from data_read_core.shared.pagination import ACTION_QUEUE, CREATED_AT_DESC;"
        "print(json.dumps({"
        "'actions': {'material': ActionFilters().as_cache_material(),"
        " 'order': ACTION_QUEUE.signature},"
        "'automations': {'material': AutomationFilters().as_cache_material(),"
        " 'order': CREATED_AT_DESC.signature}}))"
    ),
    "write-service": (
        "import json;"
        "from data_write_core.application.query_filters import ("
        "FallbackActionFilters, FallbackAutomationFilters);"
        "from write_service.common.pagination import ACTION_QUEUE, CREATED_AT_DESC;"
        "print(json.dumps({"
        "'actions': {'material': FallbackActionFilters().as_cursor_material(),"
        " 'order': ACTION_QUEUE.signature},"
        "'automations': {'material': FallbackAutomationFilters().as_cursor_material(),"
        " 'order': CREATED_AT_DESC.signature}}))"
    ),
}

# read-service keeps its filter objects beside its ORM models, so reading them
# means booting Django. write-service keeps its in an infrastructure-free module
# precisely so this does not have to boot anything.
_RUNNERS = {
    "read-service": ("uv", "run", "python", "manage.py", "shell", "-c"),
    "write-service": ("uv", "run", "python", "-c"),
}

# What the two sides must agree on for a rerouted page to continue rather than
# restart. Written down here so agreement on a WRONG order still fails.
FILTERED_ORDERS = {
    "actions": "severity_rank:desc,created_at:desc,id:desc",
    "automations": "created_at:desc,id:desc",
}


@cache
def filtered_collections() -> dict[str, dict]:
    """The filter dict and sort order each side binds a cursor to, taken from
    the service's own objects rather than restated here."""

    results = {}
    for service, script in _FILTER_MATERIAL_SCRIPTS.items():
        completed = subprocess.run(
            _RUNNERS[service] + (script,),
            cwd=REPOSITORY / "services" / service,
            capture_output=True,
            text=True,
            check=True,
        )
        results[service] = json.loads(completed.stdout[completed.stdout.index("{") :])

    return results


@cache
def go_source() -> str:
    """The Go codec and the test that pins it against the golden token.

    Read as text rather than executed: `go test` covers the encoding itself,
    and what this suite adds is that the two goldens are the same string.
    """

    return "\n".join(
        source.read_text(encoding="utf-8") for source in sorted(GO_CURSOR_PACKAGE.glob("*.go"))
    )
