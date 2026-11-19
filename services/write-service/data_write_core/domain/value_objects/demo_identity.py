from hashlib import sha256

DEMO_EXTERNAL_ID_PREFIX = "demo_"
DEMO_EXTERNAL_ID_DIGEST_HEX_LENGTH = 32
DEMO_VISIT_DERIVATION_DOMAIN = "power-finance-demo-visit"


def demo_external_id_for_visit(visit_nonce: str) -> str:
    visit_digest = sha256(f"{DEMO_VISIT_DERIVATION_DOMAIN}.{visit_nonce}".encode()).hexdigest()
    return f"{DEMO_EXTERNAL_ID_PREFIX}{visit_digest[:DEMO_EXTERNAL_ID_DIGEST_HEX_LENGTH]}"


def is_demo_external_id(external_id: str) -> bool:
    return external_id.startswith(DEMO_EXTERNAL_ID_PREFIX) and len(external_id) > len(
        DEMO_EXTERNAL_ID_PREFIX
    )
