from collections.abc import Sequence
from dataclasses import dataclass

from filter_grammar_py import FilterParseError, Record

from ..entities import AutomationEntity


@dataclass(frozen=True)
class RuleSelection:
    matched: tuple[AutomationEntity, ...]
    unreadable: tuple[AutomationEntity, ...]


def select_matching_rules(
    rules: Sequence[AutomationEntity],
    subject: Record,
) -> RuleSelection:
    matched: list[AutomationEntity] = []
    unreadable: list[AutomationEntity] = []

    for rule in rules:
        try:
            if rule.matches_subject(subject):
                matched.append(rule)
        except FilterParseError:
            unreadable.append(rule)

    return RuleSelection(
        matched=tuple(matched),
        unreadable=tuple(unreadable),
    )
