from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework.request import Request

from data_write_core.application.money_scales import load_scales

from .config import Defaults, HeaderName


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
        currency=await _resolve_currency(request.headers.get(HeaderName.CURRENCY)),
        timezone=_resolve_timezone(request.headers.get(HeaderName.TIMEZONE)),
        language=_resolve_language(request.headers.get(HeaderName.LANGUAGE)),
    )


async def _resolve_currency(raw_currency: str | None) -> str:
    if not raw_currency:
        return Defaults.CURRENCY

    currency_candidate = raw_currency.strip().upper()
    return currency_candidate if currency_candidate in await load_scales() else Defaults.CURRENCY


def _resolve_timezone(raw_timezone: str | None) -> str:
    if not raw_timezone:
        return Defaults.TIMEZONE

    timezone_candidate = raw_timezone.strip()
    try:
        ZoneInfo(timezone_candidate)
    except (ZoneInfoNotFoundError, ValueError):
        return Defaults.TIMEZONE

    return timezone_candidate


def _resolve_language(raw_language: str | None) -> str:
    if not raw_language:
        return Defaults.LANGUAGE

    language_candidate = raw_language.strip()
    return language_candidate if _looks_like_language_tag(language_candidate) else Defaults.LANGUAGE


def _looks_like_language_tag(candidate: str) -> bool:
    if not 2 <= len(candidate) <= 35:
        return False

    return all(part.isalnum() for part in candidate.split("-") if part)
