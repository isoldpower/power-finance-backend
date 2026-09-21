from enum import StrEnum


class HeaderName(StrEnum):
    GATEWAY_USER = "X-User-Id"
    CURRENCY = "X-User-Currency"
    TIMEZONE = "X-User-Timezone"
    LANGUAGE = "X-User-Language"


class Defaults(StrEnum):
    CURRENCY = "USD"
    TIMEZONE = "UTC"
    LANGUAGE = "en"


class SchemaName(StrEnum):
    SECURITY = "clerkBearer"
