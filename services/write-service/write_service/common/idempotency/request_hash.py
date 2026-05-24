import hashlib
import json
from typing import Any


def fingerprint(method: str, path: str, body: Any) -> str:
    """Served to provide hashed function call to provide creating/restoring historical responses"""
    canonical_body = _canonical_body(body)

    h = hashlib.sha256()
    h.update(method.upper().encode("utf-8"))
    h.update(b"\x00")
    h.update(path.encode("utf-8"))
    h.update(b"\x00")
    h.update(canonical_body.encode("utf-8"))

    return h.hexdigest()


def _canonical_body(body: bytes | bytearray | str | None) -> str:
    """Use to translate body to the stable presentation
    (e.g. same logical input is translated to same output)"""
    if body is None or body == "":
        return ""

    parsed: Any
    if isinstance(body, bytes | bytearray):
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return hashlib.sha256(bytes(body)).hexdigest()
    elif isinstance(body, str):
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return body
    else:
        parsed = body

    return json.dumps(
        parsed,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
