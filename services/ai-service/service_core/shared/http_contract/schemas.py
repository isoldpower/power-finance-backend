"""The envelope as published schema, not just as a runtime dict.

Without these the generated document says `object` and declares no failures,
so a client generated from it gets an untyped dictionary and no idea that a
request can be refused. read-service and write-service publish precise
envelopes; this is the same contract, spelled for FastAPI.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetailSchema(BaseModel):
    field: str
    code: str
    message: str


class ErrorBodySchema(BaseModel):
    code: str = Field(description="The `error.code` from Conventions → Error Codes.")
    message: str
    details: list[ErrorDetailSchema] | None = Field(
        default=None,
        description="Present only for a failure that names the fields it refused.",
    )


class ErrorMetaSchema(BaseModel):
    request_id: str | None = Field(
        default=None,
        description="The correlation id the request carried, when it carried one.",
    )
    timestamp: str


class ErrorResponseSchema(BaseModel):
    error: ErrorBodySchema
    meta: ErrorMetaSchema


class CollectionMetaSchema(BaseModel):
    limit: int | None = Field(description="Effective page size. Null on non-paginated endpoints.")
    total: int = Field(description="Total items matching the request, ignoring pagination.")
    next_cursor: str | None = Field(
        description="Opaque token for the page after this one. Null when exhausted."
    )
    prev_cursor: str | None = Field(
        description="Opaque token for the page before this one. Null on the first page."
    )


class CachedMetaSchema(BaseModel):
    cached: bool = Field(description="Whether this response was served from a cache.")


class EmptyMetaSchema(BaseModel):
    """`meta` is `{}` rather than absent when there is nothing to say."""


# The failures every endpoint here can produce. Declared per-router so a
# generated client knows a call can be refused.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponseSchema, "description": "Did not traverse the API gateway."},
    422: {"model": ErrorResponseSchema, "description": "A parameter was refused."},
}
