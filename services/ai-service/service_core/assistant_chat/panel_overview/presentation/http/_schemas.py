from pydantic import BaseModel, Field

from service_core.shared.http_contract import CachedMetaSchema


class SignalSchema(BaseModel):
    label: str
    value: str = Field(
        description=(
            "PREFORMATTED display text and the one deliberate formatting exception "
            "in this API. Rendered verbatim; never parsed back into a number."
        ),
    )
    tone: str = Field(description="`positive`, `negative` or `muted`.")


class OverviewSchema(BaseModel):
    signals: list[SignalSchema]
    prompts: list[str] = Field(
        description="Suggestion chips. Not a closed set and not stable between requests.",
    )


class OverviewResponseSchema(BaseModel):
    data: OverviewSchema
    meta: CachedMetaSchema
