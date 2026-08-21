import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed

CANONICAL_AMOUNT = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")
MAX_INTEGER_DIGITS = 18

MINUS_SIGN = "-"
DECIMAL_POINT = "."


@dataclass(frozen=True)
class AmountCandidate:
    """A raw request value being read as an amount at a known currency scale."""

    raw: object
    decimals: int

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

    @property
    def fraction_digits(self) -> int:
        _, _, fraction = self.text.partition(DECIMAL_POINT)

        return len(fraction)


class AmountRule(ABC):
    """One reason a request amount is rejected."""

    code: DetailCode = DetailCode.AMOUNT_MALFORMED

    @abstractmethod
    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def message(self, candidate: AmountCandidate) -> str:
        raise NotImplementedError()


class TextOnlyRule(AmountRule):
    """A JSON number here means a client regressed to floats."""

    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.is_text

    def message(self, candidate: AmountCandidate) -> str:
        return "Amount must be a decimal string, not a JSON number"


class CanonicalFormRule(AmountRule):
    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.is_canonical

    def message(self, candidate: AmountCandidate) -> str:
        return (
            "Amount must be a canonical decimal string with no separators, "
            "exponent, or leading zeros"
        )


class IntegerDigitsRule(AmountRule):
    code = DetailCode.AMOUNT_OUT_OF_RANGE

    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.integer_digits <= MAX_INTEGER_DIGITS

    def message(self, candidate: AmountCandidate) -> str:
        return f"Integer part exceeds {MAX_INTEGER_DIGITS} digits"


class CurrencyScaleRule(AmountRule):
    """Fewer fraction digits than the scale are zero-padded; more are rejected
    rather than rounded."""

    code = DetailCode.AMOUNT_PRECISION

    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.fraction_digits <= candidate.decimals

    def message(self, candidate: AmountCandidate) -> str:
        return (
            f"Currency allows {candidate.decimals} fraction digits, "
            f"got {candidate.fraction_digits}"
        )


# Order matters: every later rule reads a string the earlier ones vouched for.
AMOUNT_RULES: tuple[AmountRule, ...] = (
    TextOnlyRule(),
    CanonicalFormRule(),
    IntegerDigitsRule(),
    CurrencyScaleRule(),
)


@dataclass(frozen=True)
class AmountParser:
    """Reads a request amount, rejecting at the first rule it breaks."""

    rules: tuple[AmountRule, ...] = AMOUNT_RULES

    def parse(self, raw: object, decimals: int, field: str) -> Decimal:
        candidate = AmountCandidate(raw=raw, decimals=decimals)
        self._enforce(candidate, field)

        try:
            return Decimal(candidate.text)
        except InvalidOperation as exc:  # pragma: no cover - the rules reject these first
            raise _failure(field, DetailCode.AMOUNT_MALFORMED, "Amount is not a decimal") from exc

    def _enforce(self, candidate: AmountCandidate, field: str) -> None:
        for rule in self.rules:
            if not rule.is_satisfied_by(candidate):
                raise _failure(field, rule.code, rule.message(candidate))


AMOUNT_PARSER = AmountParser()


def parse_amount(raw: object, decimals: int, field: str) -> Decimal:
    return AMOUNT_PARSER.parse(raw, decimals, field)


def _failure(field: str, code: DetailCode, message: str) -> ValidationFailed:
    return ValidationFailed(details=[ErrorDetail(field=field, code=code, message=message)])
