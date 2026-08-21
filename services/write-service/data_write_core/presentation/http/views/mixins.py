from typing import Any

from rest_framework.response import Response
from write_service.common.http_contract import ok


class CommandResponseMixin:
    """Every mutation answers the same way: the affected resource in `data`, the
    write version in a header."""

    def form_write_response(
        self,
        write_version: int,
        response_body: Any,
        status_code: int,
        meta: dict[str, Any] | None = None,
    ) -> Response:
        return ok(
            response_body,
            meta or {},
            status_code=status_code,
            headers={"X-Write-Version": str(write_version)},
        )
