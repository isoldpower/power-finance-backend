from ..rate_snapshot import RateSnapshot
from .rate_snapshot_dto import RateSnapshotDTO


def rate_snapshot_to_dto(snapshot: RateSnapshot) -> RateSnapshotDTO:
    return RateSnapshotDTO(
        base=snapshot.base,
        rates=snapshot.rates,
        fetched_at=snapshot.fetched_at,
    )


def dto_to_rate_snapshot(dto: RateSnapshotDTO) -> RateSnapshot:
    return RateSnapshot(
        base=dto.base,
        rates=dto.rates,
        fetched_at=dto.fetched_at,
    )
