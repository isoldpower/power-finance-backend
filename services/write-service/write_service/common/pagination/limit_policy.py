from dataclasses import dataclass

from write_service.common.http_contract import DetailCode, ErrorDetail, ValidationFailed

from .config import (
    DEFAULT_LIMIT,
    LIMIT_PARAMETER_NAME,
    MAXIMUM_LIMIT,
    MINIMUM_LIMIT,
    NON_INTEGER_LIMIT_MESSAGE,
)


@dataclass(frozen=True)
class LimitPolicy:
    """The page sizes a collection answers."""

    default: int = DEFAULT_LIMIT
    minimum: int = MINIMUM_LIMIT
    maximum: int = MAXIMUM_LIMIT

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
                        field=LIMIT_PARAMETER_NAME,
                        code=DetailCode.INVALID,
                        message=NON_INTEGER_LIMIT_MESSAGE,
                    )
                ]
            ) from exc

    def _clamp(self, requested: int) -> int:
        return max(self.minimum, min(self.maximum, requested))


DEFAULT_LIMIT_POLICY = LimitPolicy()
