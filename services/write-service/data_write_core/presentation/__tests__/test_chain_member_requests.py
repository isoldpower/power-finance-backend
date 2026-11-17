from data_write_core.presentation.http.serializers import (
    AttachChainTransactionRequestSerializer,
    CreateTransactionChainRequestSerializer,
)

WALLET = "11111111-1111-1111-1111-111111111111"
EXISTING = "ffffffff-ffff-ffff-ffff-ffffffffffff"

NEW_TRANSACTION = {
    "name": "Transfer fee",
    "wallet_id": WALLET,
    "currency": "USD",
    "amount": "2.50",
    "type": "expense",
}


def test_a_new_transaction_body_is_accepted():
    serializer = AttachChainTransactionRequestSerializer(data=NEW_TRANSACTION)

    assert serializer.is_valid(), serializer.errors
    assert "transaction_id" not in serializer.validated_data


def test_a_bare_transaction_id_is_accepted():
    serializer = AttachChainTransactionRequestSerializer(data={"transaction_id": EXISTING})

    assert serializer.is_valid(), serializer.errors
    assert str(serializer.validated_data["transaction_id"]) == EXISTING


def test_a_transaction_id_cannot_come_with_new_transaction_fields():
    serializer = AttachChainTransactionRequestSerializer(
        data={"transaction_id": EXISTING, "amount": "2.50", "name": "Fee"}
    )

    assert not serializer.is_valid()
    assert set(serializer.errors) == {"amount", "name"}


def test_a_new_transaction_needs_its_required_fields():
    serializer = AttachChainTransactionRequestSerializer(data={"name": "Fee"})

    assert not serializer.is_valid()
    assert set(serializer.errors) == {"wallet_id", "currency", "amount", "type"}
    assert serializer.errors["amount"][0].code == "required"


def test_a_chain_mixes_new_and_existing_entries():
    serializer = CreateTransactionChainRequestSerializer(
        data={
            "transactions": [
                {"temporary_id": "out", "transaction_id": EXISTING},
                {"temporary_id": "in", "after": "out", **NEW_TRANSACTION},
            ]
        }
    )

    assert serializer.is_valid(), serializer.errors
