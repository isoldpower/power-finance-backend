import json
from decimal import Decimal, InvalidOperation

import httpx

from ...application.contracts import RateUnavailable
from ...application.dtos import RateSnapshotDTO
from ..logging import log_provider_failed, log_provider_refused
from .mappers import OpenExchangeMapper


class OpenExchangeRatesProvider:
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

    async def fetch(self, base_code: str) -> RateSnapshotDTO:
        payload = await self._get(base_code)

        if not OpenExchangeMapper.is_success(payload):
            log_provider_refused(self.name, base_code, OpenExchangeMapper.error_type(payload))
            raise RateUnavailable(f"rate feed has no rates for {base_code}")

        return self._to_dto(base_code, payload)

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
            raise RateUnavailable(f"rate feed is unreachable for {base_code}") from unreachable

    def _to_dto(self, base_code: str, payload: dict) -> RateSnapshotDTO:
        try:
            return OpenExchangeMapper.to_dto(base_code, payload)
        except (KeyError, AttributeError, InvalidOperation, TypeError) as malformed:
            log_provider_failed(self.name, base_code, malformed)

            raise RateUnavailable("rate feed returned a payload we cannot read") from malformed
