from collections.abc import Mapping
from typing import Any

from ...vocabulary import EffectType
from ..fields import refuse, require_money, require_uuid
from .base import EffectRule


class TransferRule(EffectRule):
    effect_type = EffectType.TRANSFER
    required_params = frozenset({"from_wallet_id", "to_wallet_id", "money"})

    def check_values(self, params: Mapping[Any, Any], path: str) -> None:
        source = require_uuid(params, "from_wallet_id", path)
        target = require_uuid(params, "to_wallet_id", path)
        if source == target:
            raise refuse(path, "A transfer needs two different wallets.")

        require_money(params.get("money"), f"{path}.money")
