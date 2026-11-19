from data_read_core.shared.analytics import AnalyticsScope, present_scope_meta
from data_read_core.shared.money import money_at_scale

from ..dtos import RhythmCellDTO, SpendingRhythmDTO


async def present_spending_rhythm(rhythm: SpendingRhythmDTO, currency: str) -> dict:
    return {
        "type": rhythm.side.value,
        "cells": [await _present_cell(cell, currency) for cell in rhythm.cells],
        "peak": await _present_peak(rhythm.peak, currency),
    }


def present_meta(scope: AnalyticsScope, cached: bool) -> dict:
    return present_scope_meta(scope, cached)


async def _present_cell(cell: RhythmCellDTO, currency: str) -> dict:
    return {
        "weekday": cell.iso_weekday,
        "hour": cell.hour,
        "amount": await money_at_scale(cell.amount, currency),
        "transactions_count": cell.transactions_count,
    }


async def _present_peak(peak_cell: RhythmCellDTO | None, currency: str) -> dict | None:
    if peak_cell is None:
        return None

    return {
        "weekday": peak_cell.iso_weekday,
        "hour": peak_cell.hour,
        "amount": await money_at_scale(peak_cell.amount, currency),
    }
