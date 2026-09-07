from ...domain.entities import (
    ConversationActivity,
    Overview,
    Signal,
    SignalTone,
)
from .activity_dto import ConversationActivityDTO
from .overview_dto import OverviewDTO, SignalDTO


def activity_to_dto(activity: ConversationActivity) -> ConversationActivityDTO:
    return ConversationActivityDTO(
        spend_currency=activity.spend_currency,
        spend_this_month=activity.spend_this_month,
        spend_last_month=activity.spend_last_month,
        uncategorised=activity.uncategorised,
        recorded_this_month=activity.recorded_this_month,
    )


def dto_to_activity(dto: ConversationActivityDTO) -> ConversationActivity:
    return ConversationActivity(
        spend_currency=dto.spend_currency,
        spend_this_month=dto.spend_this_month,
        spend_last_month=dto.spend_last_month,
        uncategorised=dto.uncategorised,
        recorded_this_month=dto.recorded_this_month,
    )


def signal_to_dto(signal: Signal) -> SignalDTO:
    return SignalDTO(label=signal.label, value=signal.value, tone=str(signal.tone))


def dto_to_signal(dto: SignalDTO) -> Signal:
    return Signal(label=dto.label, value=dto.value, tone=SignalTone(dto.tone))


def overview_to_dto(overview: Overview) -> OverviewDTO:
    return OverviewDTO(
        signals=tuple(signal_to_dto(signal) for signal in overview.signals),
        prompts=overview.prompts,
    )


def dto_to_overview(dto: OverviewDTO) -> Overview:
    return Overview(
        signals=tuple(dto_to_signal(signal) for signal in dto.signals),
        prompts=dto.prompts,
    )
