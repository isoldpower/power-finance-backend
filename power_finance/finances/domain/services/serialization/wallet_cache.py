import dataclasses
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from finances.application.dtos import WalletDTO


def serialize_wallet_dto(dto: WalletDTO) -> str:
    d = dataclasses.asdict(dto)
    d['id'] = str(d['id'])
    d['balance_amount'] = str(d['balance_amount'])
    d['created_at'] = d['created_at'].isoformat()
    d['updated_at'] = d['updated_at'].isoformat()

    return json.dumps(d)


def deserialize_wallet_dto(raw: str) -> WalletDTO:
    d = json.loads(raw)
    return WalletDTO(
        id=UUID(d['id']),
        user_id=d['user_id'],
        name=d['name'],
        balance_amount=Decimal(d['balance_amount']),
        currency=d['currency'],
        credit=d['credit'],
        created_at=datetime.fromisoformat(d['created_at']),
        updated_at=datetime.fromisoformat(d['updated_at']),
    )