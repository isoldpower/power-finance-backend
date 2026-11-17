from rest_framework.request import Request

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed
from data_read_core.shared.postgres_orm import CategoryKinds

from ..config import Messages, ParamsList


def resolve_kind(request: Request) -> str | None:
    raw_kind = request.query_params.get(ParamsList.KIND)
    if raw_kind is None or raw_kind == "":
        return None

    legal_kinds = [kind.value for kind in CategoryKinds]
    if raw_kind not in legal_kinds:
        raise ValidationFailed(
            details=[
                ErrorDetail(
                    field=ParamsList.KIND,
                    code=DetailCode.INVALID,
                    message=Messages.UNKNOWN_KIND.format(legal=", ".join(legal_kinds)),
                )
            ]
        )

    return raw_kind
