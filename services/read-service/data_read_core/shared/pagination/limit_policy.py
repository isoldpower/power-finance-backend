from dataclasses import dataclass

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
)

from .config import (
    LIMITS,
    NON_INTEGER_MESSAGE,
    PARAMETER_NAMES,
)


@dataclass(frozen=True)
class LimitPolicy:
    default: int = LIMITS["DEFAULT"]
    minimum: int = LIMITS["MINIMUM"]
    maximum: int = LIMITS["MAXIMUM"]
    parameter: str = PARAMETER_NAMES["LIMIT"]

    def resolve(self, raw_policy: str | None) -> int:
        if not raw_policy:
            return self.default

        return self._clamp_limit(
            self._parse_policy(raw_policy),
        )

    def _parse_policy(self, raw_policy: str) -> int:
        try:
            return int(raw_policy)
        except (TypeError, ValueError) as exc:
            raise ValidationFailed(
                details=[
                    ErrorDetail(
                        field=self.parameter,
                        code=DetailCode.INVALID,
                        message=NON_INTEGER_MESSAGE.format(
                            parameter=self.parameter,
                        ),
                    )
                ]
            ) from exc

    def _clamp_limit(self, requested: int) -> int:
        return max(
            self.minimum,
            min(self.maximum, requested),
        )


DEFAULT_LIMIT_POLICY = LimitPolicy()
