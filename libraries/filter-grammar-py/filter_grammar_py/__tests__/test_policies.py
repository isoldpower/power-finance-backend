"""The policy tables themselves.

They are data, but they are the contract two services agree on, so the shape
they must keep is asserted rather than assumed.
"""

import pytest

from filter_grammar_py import (
    FILTER_POLICIES,
    FilterResource,
    TypeVariant,
    policy_for,
)


def test_every_named_resource_has_a_policy():
    for resource in (
        FilterResource.TRANSACTIONS,
        FilterResource.WALLETS,
        FilterResource.WEBHOOKS,
    ):
        assert policy_for(resource)


@pytest.mark.parametrize("resource", sorted(FILTER_POLICIES))
def test_a_field_declares_the_operators_it_answers(resource: str):
    for request_name, field_policy in policy_for(resource).items():
        assert field_policy.request_name == request_name
        assert field_policy.allowed_operators
        assert isinstance(field_policy.value_type, TypeVariant)


@pytest.mark.parametrize("resource", sorted(FILTER_POLICIES))
def test_every_field_can_be_reached_by_at_least_one_store(resource: str):
    """A field with neither an ORM lookup nor an Elasticsearch field is one a
    client may send and nothing can answer."""

    for field_policy in policy_for(resource).values():
        assert field_policy.model_lookup or field_policy.es_field
