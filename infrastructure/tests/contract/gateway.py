"""Kong's declarative config, read the way Kong reads it.

Not a full router — enough of one to answer "which service would this path
reach", which is the question a misplaced route gets wrong.
"""

import re
from dataclasses import dataclass
from functools import cache

import yaml

from .documents import KONG_CONFIG

REGEX_MARKER = "~"


@dataclass(frozen=True, slots=True)
class Route:
    service: str
    name: str
    path: str
    methods: frozenset[str]
    regex_priority: int

    @property
    def is_regex(self) -> bool:
        return self.path.startswith(REGEX_MARKER)

    def matches(self, path: str, method: str) -> bool:
        if self.methods and method not in self.methods:
            return False
        if self.is_regex:
            return re.search(self.path[1:], path) is not None

        return path.startswith(self.path)

    @property
    def specificity(self) -> tuple[int, int, int]:
        """Kong prefers a regex route, then a higher `regex_priority`, then a
        longer prefix."""

        return (int(self.is_regex), self.regex_priority, len(self.path))


@cache
def routes() -> tuple[Route, ...]:
    config = yaml.safe_load(KONG_CONFIG.read_text(encoding="utf-8"))

    found = []
    for service in config["services"]:
        for route in service.get("routes", ()):
            for path in route["paths"]:
                found.append(
                    Route(
                        service=service["name"],
                        name=route["name"],
                        path=path,
                        methods=frozenset(route.get("methods", ())),
                        regex_priority=route.get("regex_priority", 0),
                    )
                )

    return tuple(found)


def resolve(path: str, method: str) -> Route | None:
    """The route Kong would pick, or None when nothing routes the request."""

    candidates = [route for route in routes() if route.matches(path, method)]
    if not candidates:
        return None

    return max(candidates, key=lambda route: route.specificity)


@cache
def plugin_config(service: str, plugin: str) -> dict | None:
    config = yaml.safe_load(KONG_CONFIG.read_text(encoding="utf-8"))
    entry = next(item for item in config["services"] if item["name"] == service)

    for declared in entry.get("plugins", ()):
        if declared["name"] == plugin:
            return declared.get("config", {})

    return None
