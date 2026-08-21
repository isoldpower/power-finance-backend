from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework.request import Request

from data_read_core.shared.money import CURRENCY_SCALES

from .defaults import DEFAULT_CURRENCY, DEFAULT_LANGUAGE, DEFAULT_TIMEZONE
from .headers import CURRENCY_HEADER, LANGUAGE_HEADER, TIMEZONE_HEADER


@dataclass(frozen=True)
class UserPreferences:
    currency: str
    timezone: str
    language: str

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def cache_signature(self) -> str:
        return f"{self.currency}|{self.language}|{self.timezone}"


async def resolve_preferences(request: Request) -> UserPreferences:
    return UserPreferences(
        currency=await _resolve_currency(request.headers.get(CURRENCY_HEADER)),
        timezone=_resolve_timezone(request.headers.get(TIMEZONE_HEADER)),
        language=_resolve_language(request.headers.get(LANGUAGE_HEADER)),
    )


async def _resolve_currency(raw_currency: str | None) -> str:
    if not raw_currency:
        return DEFAULT_CURRENCY

    parsed_currency = raw_currency.strip().upper()
    currency_scales = await CURRENCY_SCALES.table()

    return parsed_currency if parsed_currency in currency_scales else DEFAULT_CURRENCY


def _resolve_timezone(raw: str | None) -> str:
    if not raw:
        return DEFAULT_TIMEZONE

    candidate = raw.strip()
    try:
        ZoneInfo(candidate)
    except (ZoneInfoNotFoundError, ValueError):
        return DEFAULT_TIMEZONE

    return candidate


def _resolve_language(raw_language: str | None) -> str:
    if not raw_language:
        return DEFAULT_LANGUAGE

    language_candidate = raw_language.strip()

    return language_candidate if _looks_like_language_tag(language_candidate) else DEFAULT_LANGUAGE


def _looks_like_language_tag(candidate: str) -> bool:
    if not 2 <= len(candidate) <= 35:
        return False

    return all(part.isalnum() for part in candidate.split("-") if part)
