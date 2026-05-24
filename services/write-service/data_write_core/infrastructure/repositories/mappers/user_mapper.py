from typing import Any

from data_write_core.domain.entities import InternalUserEntity


class UserMapper:
    @staticmethod
    def to_domain(model: Any) -> InternalUserEntity:
        return InternalUserEntity(
            user_id=str(model.id),
            email=model.email,
            first_name=model.first_name,
            last_name=model.last_name,
        )
