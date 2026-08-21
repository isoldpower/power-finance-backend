from dataclasses import dataclass

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed

from .config import LIMITS, NON_INTEGER_LIMIT_MESSAGE, PARAMETER_NAMES


@dataclass(frozen=True)
class LimitPolicy:
    """The page sizes a collection answers."""

    default: int = LIMITS.get("DEFAULT")
    minimum: int = LIMITS.get("MINIMUM")
    maximum: int = LIMITS.get("MAXIMUM")

    def resolve(self, raw: str | None) -> int:
        if not raw:
            return self.default

        return self._clamp(self._parse(raw))

    def _parse(self, raw: str) -> int:
        try:
            return int(raw)
        except (TypeError, ValueError) as exc:
            raise ValidationFailed(
                details=[
                    ErrorDetail(
                        field=PARAMETER_NAMES.get("LIMIT"),
                        code=DetailCode.INVALID,
                        message=NON_INTEGER_LIMIT_MESSAGE,
                    )
                ]
            ) from exc

    def _clamp(self, requested: int) -> int:
        return max(self.minimum, min(self.maximum, requested))


DEFAULT_LIMIT_POLICY = LimitPolicy()
