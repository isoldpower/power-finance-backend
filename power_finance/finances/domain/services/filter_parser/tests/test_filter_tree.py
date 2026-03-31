"""
SQL / ORM injection validation for FilterTree + FilterPolicy.

Attack vectors tested:
  1. Classic SQL injection in values
  2. ORM field-traversal injection
  3. Lookup-type injection
  4. Operator injection
  5. Group-operator injection
  6. Nested / recursive bombs
  7. Oversized payloads
  8. Model-lookup integrity
"""
from django.test import SimpleTestCase
from django.db.models import Q

from ..filter_tree import FilterTree
from ....entities import FilterPolicy, FilterFieldPolicy
from ....exceptions import (
    PolicyViolationError,
    InvalidOperationError,
    FilterParseError,
    InvalidGroupingError,
)


class FilterTreeInjectionTest(SimpleTestCase):
    def make_policy(self) -> FilterPolicy:
        return {
            "amount": FilterFieldPolicy(
                request_name="amount", model_lookup="transaction_amount",
                allowed_operators={"eq", "gt", "lt", "gte", "lte"}, value_type=int,
            ),
            "name": FilterFieldPolicy(
                request_name="name", model_lookup="wallet__name",
                allowed_operators={"eq", "contains", "icontains"}, value_type=str,
            ),
        }

    def must_reject(self, raw, msg="should have been rejected"):
        """Assert that the filter tree rejects this input."""
        tree = FilterTree(self.make_policy())
        with self.assertRaises((PolicyViolationError, InvalidOperationError, FilterParseError,
                                InvalidGroupingError, ValueError, KeyError, TypeError), msg=msg):
            tree.resolve(raw)

    def must_accept_safe(self, raw, msg="should produce a safe Q"):
        """Assert the input is accepted and produces a Q (value is parameterised)."""
        tree = FilterTree(self.make_policy())
        q = tree.resolve(raw)
        self.assertIsInstance(q, Q, msg=msg)
        return q

    # ═══════════════════════════════════════════════════════════════════════════
    #  1. CLASSIC SQL INJECTION IN VALUES
    # ═══════════════════════════════════════════════════════════════════════════

    def test_sqli_drop_table_int_field(self):
        """'; DROP TABLE transactions;-- on int field → rejected by value_type."""
        self.must_reject({"field_name": "amount", "operator": "eq",
                         "value": "'; DROP TABLE transactions;--"})

    def test_sqli_union_select_int_field(self):
        """UNION SELECT on int field → rejected by value_type."""
        self.must_reject({"field_name": "amount", "operator": "eq",
                         "value": "1 UNION SELECT * FROM auth_user"})

    def test_sqli_or_1_eq_1_int_field(self):
        """OR 1=1 on int field → rejected by value_type."""
        self.must_reject({"field_name": "amount", "operator": "eq",
                         "value": "1 OR 1=1"})

    def test_sqli_drop_table_str_field(self):
        """SQL payload on str field → accepted (Django parameterises the value)."""
        q = self.must_accept_safe({"field_name": "name", "operator": "eq",
                                  "value": "'; DROP TABLE transactions;--"})
        self.assertEqual(q.children[0][1], "'; DROP TABLE transactions;--")

    def test_sqli_union_select_str_field(self):
        """UNION SELECT on str field → accepted safely as a literal string."""
        q = self.must_accept_safe({"field_name": "name", "operator": "eq",
                                  "value": "x' UNION SELECT password FROM auth_user--"})
        self.assertEqual(q.children[0][1], "x' UNION SELECT password FROM auth_user--")

    def test_sqli_comment_injection(self):
        """SQL comment injection → treated as literal value."""
        q = self.must_accept_safe({"field_name": "name", "operator": "contains",
                                  "value": "test'/*"})
        self.assertEqual(q.children[0][1], "test'/*")

    def test_sqli_stacked_queries(self):
        """Stacked queries → int field rejects, can't reach SQL."""
        self.must_reject({"field_name": "amount", "operator": "eq",
                         "value": "1; INSERT INTO auth_user VALUES('hacked')"})

    def test_sqli_hex_encoded(self):
        """Hex-encoded payload on int field → rejected by value_type."""
        self.must_reject({"field_name": "amount", "operator": "eq",
                         "value": "0x414243"})

    def test_sqli_null_byte(self):
        """Null byte injection → int field rejects."""
        self.must_reject({"field_name": "amount", "operator": "eq",
                         "value": "1\x00 OR 1=1"})

    # ═══════════════════════════════════════════════════════════════════════════
    #  2. ORM FIELD-TRAVERSAL INJECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def test_orm_traversal_password(self):
        """field_name='user__password' → not in policy → rejected."""
        self.must_reject({"field_name": "user__password", "operator": "eq", "value": "secret"})

    def test_orm_traversal_auth_user(self):
        """field_name='user__auth__username' → not in policy → rejected."""
        self.must_reject({"field_name": "user__auth__username", "operator": "eq", "value": "admin"})

    def test_orm_traversal_email(self):
        """field_name='owner__email' → not in policy → rejected."""
        self.must_reject({"field_name": "owner__email", "operator": "eq", "value": "a@b.com"})

    def test_orm_traversal_is_superuser(self):
        """field_name='owner__is_superuser' → not in policy → rejected."""
        self.must_reject({"field_name": "owner__is_superuser", "operator": "eq", "value": "true"})

    def test_orm_traversal_deep_chain(self):
        """field_name='a__b__c__d__e__f' → not in policy → rejected."""
        self.must_reject({"field_name": "a__b__c__d__e__f", "operator": "eq", "value": "x"})

    # ═══════════════════════════════════════════════════════════════════════════
    #  3. LOOKUP-TYPE INJECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def test_lookup_regex_injection(self):
        """field_name='amount__regex' → not in policy → rejected."""
        self.must_reject({"field_name": "amount__regex", "operator": "eq", "value": ".*"})

    def test_lookup_raw_injection(self):
        """field_name='amount__raw' → not in policy → rejected."""
        self.must_reject({"field_name": "amount__raw", "operator": "eq", "value": "1"})

    def test_lookup_extra_injection(self):
        """field_name='name__extra' → not in policy → rejected."""
        self.must_reject({"field_name": "name__extra", "operator": "eq", "value": "1"})

    def test_lookup_startswith_bypassing_policy(self):
        """field_name='name__startswith' → not in policy (even though 'name' is)."""
        self.must_reject({"field_name": "name__startswith", "operator": "eq", "value": "a"})

    def test_lookup_isnull_injection(self):
        """field_name='amount__isnull' → not in policy → rejected."""
        self.must_reject({"field_name": "amount__isnull", "operator": "eq", "value": "True"})

    # ═══════════════════════════════════════════════════════════════════════════
    #  4. OPERATOR INJECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def test_operator_sql_injection(self):
        """operator='eq; DROP TABLE' → not in enum → rejected."""
        self.must_reject({"field_name": "amount", "operator": "eq; DROP TABLE", "value": "1"})

    def test_operator_raw_sql(self):
        """operator='1=1' → not in enum → rejected."""
        self.must_reject({"field_name": "amount", "operator": "1=1", "value": "1"})

    def test_operator_regex(self):
        """operator='regex' → not a valid ComparisonOperator → rejected."""
        self.must_reject({"field_name": "amount", "operator": "regex", "value": ".*"})

    def test_operator_empty(self):
        """operator='' → not in enum → rejected."""
        self.must_reject({"field_name": "amount", "operator": "", "value": "1"})

    def test_operator_none(self):
        """operator=None → not in enum → rejected."""
        self.must_reject({"field_name": "amount", "operator": None, "value": "1"})

    # ═══════════════════════════════════════════════════════════════════════════
    #  5. GROUP-OPERATOR INJECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def test_group_unknown_operator(self):
        """Group with key 'xor' → not in GroupOperator → rejected."""
        self.must_reject({"xor": [
            {"field_name": "amount", "operator": "eq", "value": "1"},
        ]})

    def test_group_sql_key(self):
        """Group with SQL as key → rejected."""
        self.must_reject({"UNION SELECT": [
            {"field_name": "amount", "operator": "eq", "value": "1"},
        ]})

    def test_group_empty_key(self):
        """Group with empty string key → rejected."""
        self.must_reject({"": [
            {"field_name": "amount", "operator": "eq", "value": "1"},
        ]})

    # ═══════════════════════════════════════════════════════════════════════════
    #  6. STRUCTURAL ATTACKS
    # ═══════════════════════════════════════════════════════════════════════════

    def test_deeply_nested_group(self):
        """50-level deep nesting → should either work or fail gracefully (no crash)."""
        inner = {"field_name": "amount", "operator": "eq", "value": "1"}
        for _ in range(50):
            inner = {"and": [inner, {"field_name": "amount", "operator": "lt", "value": "999"}]}
        tree = FilterTree(self.make_policy())
        try:
            q = tree.resolve(inner)
            self.assertIsInstance(q, Q)
        except RecursionError:
            pass  # acceptable — Python's recursion limit protects us

    def test_empty_dict(self):
        """Empty dict → rejected (neither leaf nor group)."""
        self.must_reject({})

    def test_missing_field_name(self):
        """Missing field_name → rejected."""
        self.must_reject({"operator": "eq", "value": "1"})

    def test_missing_value(self):
        """Missing value → rejected."""
        self.must_reject({"field_name": "amount", "operator": "eq"})

    def test_missing_operator(self):
        """Missing operator → rejected."""
        self.must_reject({"field_name": "amount", "value": "1"})

    def test_extra_keys_ignored(self):
        """Extra keys alongside valid leaf → still works (not a security issue)."""
        tree = FilterTree(self.make_policy())
        q = tree.resolve({"field_name": "name", "operator": "eq", "value": "test",
                          "malicious": "'; DROP TABLE--"})
        self.assertIsInstance(q, Q)

    # ═══════════════════════════════════════════════════════════════════════════
    #  7. OVERSIZED PAYLOADS
    # ═══════════════════════════════════════════════════════════════════════════

    def test_very_long_value(self):
        """10KB value on str field → accepted safely bits by Django parameterisation."""
        q = self.must_accept_safe({"field_name": "name", "operator": "eq", "value": "A" * 10000})
        self.assertEqual(q.children[0][1], "A" * 10000)

    def test_very_long_field_name(self):
        """Very long field_name → not in policy → rejected."""
        self.must_reject({"field_name": "x" * 10000, "operator": "eq", "value": "1"})

    # ═══════════════════════════════════════════════════════════════════════════
    #  8. MODEL-LOOKUP INTEGRITY
    # ═══════════════════════════════════════════════════════════════════════════

    def test_q_uses_model_lookup_not_field_name(self):
        """Verify Q lookup key = policy.model_lookup, not the user-supplied field_name."""
        q = FilterTree(self.make_policy()).resolve(
            {"field_name": "name", "operator": "eq", "value": "test"})
        keys = [k for k, v in q.children]
        self.assertIn("wallet__name", keys)
        self.assertNotIn("name", keys)

    def test_q_contains_uses_model_lookup(self):
        """Contains lookup builds from model_lookup, not field_name."""
        q = FilterTree(self.make_policy()).resolve(
            {"field_name": "name", "operator": "contains", "value": "test"})
        keys = [k for k, v in q.children]
        self.assertIn("wallet__name__contains", keys)
        self.assertNotIn("name__contains", keys)
