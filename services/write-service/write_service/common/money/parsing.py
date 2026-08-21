import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from write_service.common.http_contract import DetailCode

CANONICAL_AMOUNT = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")
MAX_INTEGER_DIGITS = 18

MINUS_SIGN = "-"
DECIMAL_POINT = "."


@dataclass(frozen=True)
class AmountCandidate:
    """A raw request value being read as an amount."""

    raw: object

    @property
    def text(self) -> str:
        return str(self.raw)

    @property
    def is_text(self) -> bool:
        return isinstance(self.raw, str)

    @property
    def is_canonical(self) -> bool:
        return bool(CANONICAL_AMOUNT.fullmatch(self.text))

    @property
    def integer_digits(self) -> int:
        return len(self.text.lstrip(MINUS_SIGN).split(DECIMAL_POINT)[0])


class AmountRule(ABC):
    """One reason a request amount is rejected, paired with the code it reports."""

    code: DetailCode = DetailCode.AMOUNT_MALFORMED

    @abstractmethod
    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        raise NotImplementedError()


class TextOnlyRule(AmountRule):
    """A JSON number here means a client regressed to floats."""

    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.is_text


class CanonicalFormRule(AmountRule):
    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.is_canonical


class IntegerDigitsRule(AmountRule):
    code = DetailCode.AMOUNT_OUT_OF_RANGE

    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.integer_digits <= MAX_INTEGER_DIGITS


# Order matters: every later rule reads a string the earlier ones vouched for.
CURRENCY_AGNOSTIC_RULES: tuple[AmountRule, ...] = (
    TextOnlyRule(),
    CanonicalFormRule(),
    IntegerDigitsRule(),
)
