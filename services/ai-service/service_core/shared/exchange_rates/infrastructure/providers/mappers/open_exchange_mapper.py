from datetime import UTC, datetime
from decimal import Decimal

from ....application.dtos import RateSnapshotDTO
from ...config import FeedPayloadKey, FeedResult


class OpenExchangeMapper:
    @staticmethod
    def is_success(payload: dict) -> bool:
        return payload.get(FeedPayloadKey.RESULT) == FeedResult.SUCCESS

    @staticmethod
    def error_type(payload: dict) -> object:
        return payload.get(FeedPayloadKey.ERROR_TYPE)

    @staticmethod
    def to_dto(base_code: str, payload: dict) -> RateSnapshotDTO:
        return RateSnapshotDTO(
            base=base_code.upper(),
            rates=OpenExchangeMapper.read_rates(payload),
            fetched_at=OpenExchangeMapper.read_updated_at(payload),
        )

    @staticmethod
    def read_rates(payload: dict) -> dict[str, Decimal]:
        return {
            str(code).upper(): Decimal(str(rate))
            for code, rate in payload[FeedPayloadKey.RATES].items()
        }

    @staticmethod
    def read_updated_at(payload: dict) -> datetime:
        raw_timestamp = payload.get(FeedPayloadKey.UPDATED_AT)
        if not isinstance(raw_timestamp, int | float | Decimal):
            return datetime.now(UTC)

        return datetime.fromtimestamp(float(raw_timestamp), tz=UTC)
