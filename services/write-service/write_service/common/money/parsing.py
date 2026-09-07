from abc import ABC, abstractmethod
from dataclasses import dataclass

from write_service.common.http_contract import DetailCode
from write_service.common.money.config import CANONICAL_AMOUNT, AmountSymbol, MoneySettings


@dataclass(frozen=True)
class AmountCandidate:
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
        return len(self.text.lstrip(AmountSymbol.MINUS_SIGN).split(AmountSymbol.DECIMAL_POINT)[0])


class AmountRule(ABC):
    code: DetailCode = DetailCode.AMOUNT_MALFORMED

    @abstractmethod
    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        raise NotImplementedError()


class TextOnlyRule(AmountRule):
    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.is_text


class CanonicalFormRule(AmountRule):
    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.is_canonical


class IntegerDigitsRule(AmountRule):
    code = DetailCode.AMOUNT_OUT_OF_RANGE

    def is_satisfied_by(self, candidate: AmountCandidate) -> bool:
        return candidate.integer_digits <= MoneySettings.MAX_INTEGER_DIGITS


CURRENCY_AGNOSTIC_RULES: tuple[AmountRule, ...] = (
    TextOnlyRule(),
    CanonicalFormRule(),
    IntegerDigitsRule(),
)
