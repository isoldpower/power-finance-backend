from pydantic import BaseModel, Field

from service_core.shared.http_contract import (
    CollectionMetaSchema,
    EmptyMetaSchema,
)


class ResourceReferenceSchema(BaseModel):
    type: str = Field(description="A resource name from API_TARGET.md — `transaction`, `account`.")
    id: str


class MessageSchema(BaseModel):
    id: str
    created_at: str
    role: str = Field(description="`user` or `assistant`.")
    status: str = Field(
        description="`complete`, `streaming` while a reply is being produced, or `failed`.",
    )
    text: str
    refs: list[ResourceReferenceSchema] = Field(
        description="Always an array. Empty for a user message and for a reply that cites nothing.",
    )


class MessageCollectionSchema(BaseModel):
    data: list[MessageSchema]
    meta: CollectionMetaSchema


class ClearedConversationSchema(BaseModel):
    deleted: int = Field(description="How many messages went. `0` when it was already empty.")


class ClearedConversationResponseSchema(BaseModel):
    data: ClearedConversationSchema
    meta: EmptyMetaSchema
