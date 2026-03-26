from enum import Enum


class WebhookType(str, Enum):
    TransactionCreate = "transaction.created"
    TransactionUpdate = "transaction.updated"
    TransactionDelete = "transaction.deleted"
