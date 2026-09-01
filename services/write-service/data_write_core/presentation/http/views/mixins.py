from typing import Any

from rest_framework.response import Response
from write_service.common.http_contract import ok


class CommandResponseMixin:
    """Every mutation answers the same way: the affected resource in `data`, the
    write version in a header."""

    def form_write_response(
        self,
        write_version: int | None,
        response_body: Any,
        status_code: int,
        meta: dict[str, Any] | None = None,
    ) -> Response:
        """`write_version=None` omits the header entirely.

        A mutation that moved nothing outside its own resource has nothing for a
        client to wait on, and a header carrying a version it cannot use would
        invite a `Read-At-Least` on a read that was never going to change.
        """

        headers = {} if write_version is None else {"X-Write-Version": str(write_version)}

        return ok(
            response_body,
            meta or {},
            status_code=status_code,
            headers=headers,
        )
