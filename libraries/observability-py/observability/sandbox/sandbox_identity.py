import os
from contextvars import Token
from typing import cast

from opentelemetry import context as context_api
from opentelemetry.context import Context

from ..context import read_baggage_entry, write_baggage_entry
from .config import ENVIRONMENT_VARIABLE_SANDBOX_ID, SANDBOX_BAGGAGE_ENTRY_NAME


def resolve_own_sandbox_id() -> str | None:
    configured_sandbox_id = os.environ.get(ENVIRONMENT_VARIABLE_SANDBOX_ID, "").strip()

    return configured_sandbox_id or None


def current_sandbox_id() -> str | None:
    return read_baggage_entry(SANDBOX_BAGGAGE_ENTRY_NAME)


def read_sandbox_id_from_context(context: Context | None) -> str | None:
    return read_baggage_entry(SANDBOX_BAGGAGE_ENTRY_NAME, context)


def attach_sandbox_id(sandbox_id: str) -> object:
    return context_api.attach(
        write_baggage_entry(
            SANDBOX_BAGGAGE_ENTRY_NAME,
            sandbox_id,
        )
    )


def detach_sandbox_id(attachment_token: object) -> None:
    context_api.detach(
        cast(
            Token[Context],
            attachment_token,
        )
    )
