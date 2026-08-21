"""https://open.er-api.com — daily rates, no key, no attribution requirement.

Free feeds update once a day, so this provider is paired with a generous
`max_age` upstream rather than polled.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx

from ..exceptions import RateUnavailable
from ..logger_shortcuts import log_provider_failed, log_provider_refused
from ..rate_snapshot import RateSnapshot
from .rate_provider import RateProvider

RESULT_KEY = "result"
SUCCESS_RESULT = "success"
RATES_KEY = "rates"
UPDATED_AT_KEY = "time_last_update_unix"
ERROR_TYPE_KEY = "error-type"


class OpenExchangeRatesProvider(RateProvider):
    name = "open-er-api"

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def fetch(self, base_code: str) -> RateSnapshot:
        payload = await self._get(base_code)

        if payload.get(RESULT_KEY) != SUCCESS_RESULT:
            log_provider_refused(self.name, base_code, payload.get(ERROR_TYPE_KEY))
            raise RateUnavailable(f"Rate feed has no rates for {base_code}")

        return RateSnapshot(
            base=base_code,
            rates=self._read_rates(payload),
            fetched_at=self._read_updated_at(payload),
        )

    async def _get(self, base_code: str) -> dict:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.get(f"{self._base_url}/{base_code}")
                response.raise_for_status()

                return json.loads(response.text, parse_float=Decimal)
        except (httpx.HTTPError, json.JSONDecodeError) as unreachable:
            log_provider_failed(self.name, base_code, unreachable)
            raise RateUnavailable(f"Rate feed is unreachable for {base_code}") from unreachable

    def _read_rates(self, payload: dict) -> dict[str, Decimal]:
        try:
            return {
                str(code).upper(): Decimal(str(rate)) for code, rate in payload[RATES_KEY].items()
            }
        except (KeyError, AttributeError, InvalidOperation, TypeError) as malformed:
            log_provider_failed(
                self.name,
                payload.get("base_code"),
                malformed,
            )

            raise RateUnavailable("Rate feed returned a payload we cannot read") from malformed

    def _read_updated_at(self, payload: dict) -> datetime:
        raw_timestamp = payload.get(UPDATED_AT_KEY)
        if raw_timestamp is None:
            return datetime.now(UTC)

        return datetime.fromtimestamp(int(raw_timestamp), tz=UTC)
