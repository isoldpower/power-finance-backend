"""Walking a generated OpenAPI document.

The conventions in API_TARGET.md are statements about EVERY endpoint, so the
tests for them are written against whatever the services publish rather than
against a list of endpoints somebody has to remember to extend.
"""

from dataclasses import dataclass
from functools import cache
from typing import Any

from .documents import METHODS
from .surface import INTERNAL_PREFIXES, schemas

JSON = "application/json"
SUCCESS_STATUSES = tuple(str(status) for status in range(200, 300))


@dataclass(frozen=True, slots=True)
class Operation:
    service: str
    method: str
    path: str
    definition: dict
    document: dict

    def __str__(self) -> str:
        return f"{self.service} {self.method} {self.path}"

    def body_of(self, status: str) -> dict | None:
        response = self.definition.get("responses", {}).get(status)
        if not response:
            return None

        schema = response.get("content", {}).get(JSON, {}).get("schema")

        return resolve_ref(self.document, schema) if schema else None

    @property
    def success_statuses(self) -> tuple[str, ...]:
        return tuple(
            status for status in self.definition.get("responses", {}) if status in SUCCESS_STATUSES
        )

    @property
    def failure_statuses(self) -> tuple[str, ...]:
        return tuple(
            status
            for status in self.definition.get("responses", {})
            if status.isdigit() and int(status) >= 400
        )


def resolve_ref(document: dict, schema: dict) -> dict:
    """Follows `$ref` one hop at a time until the schema is inline."""

    seen = 0
    while "$ref" in schema and seen < 20:
        name = schema["$ref"].rsplit("/", 1)[-1]
        schema = document["components"]["schemas"][name]
        seen += 1

    return schema


def properties_of(document: dict, schema: dict | None) -> dict[str, dict]:
    if not schema:
        return {}

    return {
        name: resolve_ref(document, definition)
        for name, definition in schema.get("properties", {}).items()
    }


@cache
def public_operations() -> tuple[Operation, ...]:
    """Every operation on the published surface, across all three documents."""

    found = []
    for schema in schemas():
        for path, operations in schema.document.get("paths", {}).items():
            if path.startswith(INTERNAL_PREFIXES):
                continue
            for method, definition in operations.items():
                if method.upper() in METHODS:
                    found.append(
                        Operation(
                            service=schema.name,
                            method=method.upper(),
                            path=path,
                            definition=definition,
                            document=schema.document,
                        )
                    )

    return tuple(found)


def walk_properties(document: dict, schema: dict | None, depth: int = 0):
    """Yields `(name, definition)` for every property anywhere in a schema.

    A convention that only held at the top level would be no convention at all:
    money nested inside a chart point is still money.
    """

    if not schema or depth > 8:
        return

    for name, definition in properties_of(document, schema).items():
        yield name, definition
        yield from walk_properties(document, definition, depth + 1)
        items = definition.get("items")
        if items:
            resolved = resolve_ref(document, items)
            yield from walk_properties(document, resolved, depth + 1)


def all_success_bodies() -> list[tuple[Operation, str, dict]]:
    bodies = []
    for operation in public_operations():
        for status in operation.success_statuses:
            body = operation.body_of(status)
            if body is not None:
                bodies.append((operation, status, body))

    return bodies


def collection_metas() -> list[tuple[Operation, dict]]:
    """Every response whose `data` is an array — the ones the page conventions
    apply to."""

    found = []
    for operation, _, body in all_success_bodies():
        properties = properties_of(operation.document, body)
        data = properties.get("data", {})
        if data.get("type") == "array":
            found.append((operation, properties.get("meta", {})))

    return found


def is_nullable(definition: dict[str, Any]) -> bool:
    if definition.get("nullable"):
        return True

    variants = [*definition.get("anyOf", ()), *definition.get("oneOf", ())]

    return any(variant.get("type") == "null" for variant in variants)


def type_of(definition: dict[str, Any]) -> set[str]:
    declared = definition.get("type")
    if declared:
        return {declared}

    variants = [*definition.get("anyOf", ()), *definition.get("oneOf", ())]

    return {
        variant.get("type")
        for variant in variants
        if variant.get("type") and variant.get("type") != "null"
    }
