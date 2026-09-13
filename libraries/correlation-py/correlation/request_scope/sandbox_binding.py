from typing import NamedTuple

from django.http import HttpRequest
from observability import attach_sandbox_id, current_sandbox_id, detach_sandbox_id


class SandboxBinding(NamedTuple):
    sandbox_id: str | None
    attachment_token: object | None


UNBOUND_SANDBOX_BINDING = SandboxBinding(sandbox_id=None, attachment_token=None)


class SandboxBinder:
    def __init__(self, sandbox_header_name: str) -> None:
        self._sandbox_header_name = sandbox_header_name

    def bind(self, request: HttpRequest) -> SandboxBinding:
        header_sandbox_id = self._read_header_sandbox_id(request)
        if not header_sandbox_id:
            return SandboxBinding(sandbox_id=current_sandbox_id(), attachment_token=None)
        if header_sandbox_id == current_sandbox_id():
            return SandboxBinding(sandbox_id=header_sandbox_id, attachment_token=None)

        return SandboxBinding(
            sandbox_id=header_sandbox_id,
            attachment_token=attach_sandbox_id(header_sandbox_id),
        )

    def unbind(self, binding: SandboxBinding) -> None:
        if binding.attachment_token is None:
            return

        detach_sandbox_id(binding.attachment_token)

    def _read_header_sandbox_id(self, request: HttpRequest) -> str | None:
        raw_header_value = request.headers.get(self._sandbox_header_name, "").strip()

        return raw_header_value or None
