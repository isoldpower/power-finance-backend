from typing import Any

from rest_framework.response import Response
from write_service.common.http_contract import ok


class CommandResponseMixin:
    def form_write_response(
        self,
        write_version: int | None,
        response_body: Any,
        status_code: int,
        meta: dict[str, Any] | None = None,
    ) -> Response:
        headers = {} if write_version is None else {"X-Write-Version": str(write_version)}

        return ok(
            response_body,
            meta or {},
            status_code=status_code,
            headers=headers,
        )
