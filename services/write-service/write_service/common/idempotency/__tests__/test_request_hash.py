from django.test import SimpleTestCase

from write_service.common.idempotency.request_hash import fingerprint


class FingerprintTests(SimpleTestCase):
    def test_identical_inputs_produce_identical_hash(self) -> None:
        a = fingerprint("POST", "/api/v1/transactions/", {"amount": "10.00", "wallet": "x"})
        b = fingerprint("POST", "/api/v1/transactions/", {"amount": "10.00", "wallet": "x"})
        self.assertEqual(a, b)

    def test_body_key_order_does_not_affect_hash(self) -> None:
        a = fingerprint("POST", "/p", {"a": 1, "b": 2})
        b = fingerprint("POST", "/p", {"b": 2, "a": 1})
        self.assertEqual(a, b)

    def test_different_method_changes_hash(self) -> None:
        a = fingerprint("POST", "/p", {"x": 1})
        b = fingerprint("PATCH", "/p", {"x": 1})
        self.assertNotEqual(a, b)

    def test_different_path_changes_hash(self) -> None:
        a = fingerprint("POST", "/p1", {"x": 1})
        b = fingerprint("POST", "/p2", {"x": 1})
        self.assertNotEqual(a, b)

    def test_different_body_changes_hash(self) -> None:
        a = fingerprint("POST", "/p", {"x": 1})
        b = fingerprint("POST", "/p", {"x": 2})
        self.assertNotEqual(a, b)

    def test_method_case_insensitive(self) -> None:
        a = fingerprint("post", "/p", {})
        b = fingerprint("POST", "/p", {})
        self.assertEqual(a, b)

    def test_empty_body_stable(self) -> None:
        a = fingerprint("DELETE", "/p", None)
        b = fingerprint("DELETE", "/p", "")
        self.assertEqual(a, b)
