def delete_transaction_with_response(transaction) -> tuple[dict, bool]:
    try:
        transaction_id = transaction.id
        transaction.delete()
        return {
            "message": "Transaction deleted successfully",
            "meta": {
                "id": str(transaction_id),
                "deleted": True
            }
        }, True
    except Exception as e:
        return {
            "message": str(e),
            "meta": {
                "id": str(transaction_id),
                "deleted": False
            }
        }, False