from enum import Enum


class WebhookType(str, Enum):
    TransactionCreate = "transaction.create"
