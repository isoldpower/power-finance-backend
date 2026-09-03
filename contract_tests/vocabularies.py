"""The two closed error vocabularies, read from the target and from the code.

A code the services can emit but the document does not list is a surprise for
every client; a code the document promises but nothing can raise is a
capability that quietly does not exist.
"""

import json
import re
import subprocess
from functools import cache

from .documents import REPOSITORY, TARGET

_CODE_CELL = re.compile(r"^\|\s*`([a-z_]+)`\s*\|")
_DETAIL_TABLE_HEADER = re.compile(r"^\|\s*detail code\s*\|", re.IGNORECASE)
_STATUS_CELL = re.compile(r"^\|\s*`[a-z_]+`\s*\|\s*(\d{3})\s*\|")

ERROR_CODES_HEADING = "#### Error Codes"
DETAIL_CODES_HEADING = "#### Detail Codes"
NEXT_SECTION = "###"

# Each service keeps the status beside its code, but not in the same way: two
# carry it on the enum member and write-service keeps a separate table. The
# reader accepts either rather than forcing a refactor for a test's benefit.
_STATUS_OF = (
    "lambda registry, code: ("
    "registry['STATUS_FOR_ERROR_CODE'][code]"
    " if 'STATUS_FOR_ERROR_CODE' in registry else code.status_code)"
)

# Imported WITHOUT `django.setup()`: the code tables are plain enums over DRF's
# status constants, and booting the app registry would open this service's
# ImmuDB and Kafka connections to read a list of strings.
CODE_SCRIPT = (
    "import json;"
    "import importlib;"
    "module = importlib.import_module({module!r});"
    "registry = vars(module);"
    "status_of = " + _STATUS_OF + ";"
    "print(json.dumps({{"
    "'error': {{str(code): status_of(registry, code) for code in registry['ErrorCode']}},"
    "'detail': [str(code) for code in registry['DetailCode']]}}))"
)

SERVICE_CODE_MODULES = {
    "read-service": "data_read_core.shared.http_contract",
    "write-service": "write_service.common.http_contract",
    "ai-service": "service_core.shared.http_contract",
}


def _section(heading: str) -> str:
    document = TARGET.read_text(encoding="utf-8")
    start = document.index(heading) + len(heading)
    end = document.index(NEXT_SECTION, start)

    return document[start:end]


@cache
def target_error_codes() -> dict[str, int]:
    rows = {}
    for line in _section(ERROR_CODES_HEADING).splitlines():
        code, status = _CODE_CELL.match(line), _STATUS_CELL.match(line)
        if code and status:
            rows[code.group(1)] = int(status.group(1))

    return rows


@cache
def target_detail_codes() -> frozenset[str]:
    """`details[].code` is documented in TWO tables.

    The `#### Detail Codes` section holds the general vocabulary; the filter
    grammar keeps its own table beside the grammar it belongs to. Reading only
    the first would report every `filter_*` code as undocumented.
    """

    codes = {
        row.group(1)
        for line in _section(DETAIL_CODES_HEADING).splitlines()
        if (row := _CODE_CELL.match(line))
    }

    return frozenset(codes | _tabled_detail_codes())


def _tabled_detail_codes() -> set[str]:
    """Rows of any table whose first column is headed "detail code"."""

    codes: set[str] = set()
    inside = False
    for line in TARGET.read_text(encoding="utf-8").splitlines():
        if _DETAIL_TABLE_HEADER.match(line):
            inside = True
            continue
        if inside:
            row = _CODE_CELL.match(line)
            if row:
                codes.add(row.group(1))
            elif not line.startswith("|"):
                inside = False

    return codes


def _read_codes(service: str, module: str) -> dict:
    completed = subprocess.run(
        ("uv", "run", "python", "-c", CODE_SCRIPT.format(module=module)),
        cwd=REPOSITORY / "services" / service,
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(completed.stdout[completed.stdout.index("{") :])


@cache
def service_codes() -> dict[str, dict]:
    return {
        service: _read_codes(service, module) for service, module in SERVICE_CODE_MODULES.items()
    }
