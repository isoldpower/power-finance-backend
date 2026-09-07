from enum import StrEnum


class LoggerSettings(StrEnum):
    ROOT = "ai_service"


class LoggerChannel(StrEnum):
    ACCOUNTS = "accounts"
    DISPATCH = "dispatch"
    PROJECTION = "projection"
