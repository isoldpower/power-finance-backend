from dataclasses import dataclass

from write_service.common.http_contract import DetailCode, ErrorDetail, ValidationFailed

from .config import (
    LimitSettings,
    Messages,
    ParamsList,
)


@dataclass(frozen=True)
class LimitPolicy:
    default: int = int(LimitSettings.DEFAULT)
    minimum: int = int(LimitSettings.MINIMUM)
    maximum: int = int(LimitSettings.MAXIMUM)

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
                        field=ParamsList.LIMIT,
                        code=DetailCode.INVALID,
                        message=Messages.NON_INTEGER_LIMIT,
                    )
                ]
            ) from exc

    def _clamp(self, requested: int) -> int:
        return max(self.minimum, min(self.maximum, requested))


DEFAULT_LIMIT_POLICY = LimitPolicy()
