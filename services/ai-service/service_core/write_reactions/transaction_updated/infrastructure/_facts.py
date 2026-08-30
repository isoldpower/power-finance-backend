from service_core.shared.db_connection import ProjectedTransaction

from ..contracts import TransactionFacts


def facts_of(row: ProjectedTransaction) -> TransactionFacts:
    return TransactionFacts(
        id=row.id,
        user_id=row.user_id,
        container_id=row.container_id,
        container_kind=row.container_kind,
        amount=row.amount,
        created_at=row.created_at,
        name=row.name,
        category=row.category,
        evidence_url=row.evidence_url,
        origin=row.origin,
        chain_id=row.chain_id,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )
