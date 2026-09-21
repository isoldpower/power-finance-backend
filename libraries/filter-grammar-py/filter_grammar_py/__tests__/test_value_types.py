"""What a type means, in the one place that decides it.

Each variant answers two different questions, and the tests are split the same
way: `accepts` guards what a CLIENT may send, `coerce` normalises what is
COMPARED. They are deliberately not the same rule — a stored `Decimal` compares
fine, but a JSON number on the wire is a client that regressed to floats.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from filter_grammar_py import UncomparableValue, value_type_for
from filter_grammar_py.value_types import VALUE_TYPES
from filter_grammar_py.vocabulary import TypeVariant


def accepts(variant: TypeVariant, value) -> bool:
    return value_type_for(variant).accepts(value)


def coerce(variant: TypeVariant, value):
    return value_type_for(variant).coerce(value)


def test_every_variant_has_a_type():
    """A variant with no type is a policy that saves and then fails at run
    time, so the gap is caught here rather than in a user's rule."""

    assert set(VALUE_TYPES) == set(TypeVariant)


def test_each_type_answers_for_its_own_variant():
    assert all(variant is value_type.variant for variant, value_type in VALUE_TYPES.items())


@pytest.mark.parametrize("value", ["100.00", "-4.5", "0"])
def test_decimals_accept_canonical_strings(value):
    assert accepts(TypeVariant.DECIMAL, value)


@pytest.mark.parametrize("value", [100, 100.0, "1e3", "+100.00", True, None])
def test_decimals_refuse_anything_that_is_not_one(value):
    assert not accepts(TypeVariant.DECIMAL, value)


def test_a_decimal_that_is_refused_on_the_wire_still_coerces_for_comparison():
    """The asymmetry is the point: the client may not SEND `100`, but a stored
    amount read back as an int must still compare."""

    assert not accepts(TypeVariant.DECIMAL, 100)
    assert coerce(TypeVariant.DECIMAL, 100) == Decimal("100")


def test_decimals_coerce_numerically_so_scale_does_not_matter():
    assert coerce(TypeVariant.DECIMAL, "-4.5") == coerce(TypeVariant.DECIMAL, "-4.500")


def test_floats_refuse_exponents_they_could_otherwise_parse():
    """`float("1e3")` works; the grammar still refuses it, because a filter is
    a client contract rather than a parser."""

    assert not accepts(TypeVariant.FLOAT, "1e3")
    assert coerce(TypeVariant.FLOAT, "1e3") == 1000.0


@pytest.mark.parametrize("value", [True, False, "true", "FALSE", "1", "0"])
def test_booleans_accept_both_spellings(value):
    assert accepts(TypeVariant.BOOLEAN, value)


def test_booleans_coerce_python_and_wire_spellings_alike():
    assert coerce(TypeVariant.BOOLEAN, True) is True
    assert coerce(TypeVariant.BOOLEAN, "FALSE") is False


def test_timestamps_are_read_as_utc_when_they_carry_no_zone():
    assert coerce(TypeVariant.DATETIME, "2026-09-01T12:00:00") == datetime(
        2026, 9, 1, 12, 0, tzinfo=UTC
    )


def test_an_instant_is_not_round_tripped_through_a_string():
    moment = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)

    assert coerce(TypeVariant.DATETIME, moment) is moment


def test_uuids_coerce_to_one_spelling():
    assert coerce(TypeVariant.UUID, "1665B60E-BB7A-4360-8AA6-C1A578D81077") == (
        "1665b60e-bb7a-4360-8aa6-c1a578d81077"
    )


def test_strings_accept_anything_and_coerce_it():
    assert accepts(TypeVariant.STRING, 7)
    assert coerce(TypeVariant.STRING, 7) == "7"


@pytest.mark.parametrize(
    ("variant", "value"),
    [
        (TypeVariant.INTEGER, "seven"),
        (TypeVariant.FLOAT, "seven"),
        (TypeVariant.DECIMAL, "not-money"),
        (TypeVariant.BOOLEAN, "maybe"),
        (TypeVariant.DATETIME, "not-a-date"),
        (TypeVariant.UUID, "not-a-uuid"),
    ],
)
def test_a_value_that_cannot_be_coerced_says_so(variant, value):
    with pytest.raises(UncomparableValue):
        coerce(variant, value)


def test_a_list_is_accepted_element_by_element():
    """`in` takes an array, and one bad element makes the whole filter
    invalid — the check is per element rather than on the array."""

    decimals = value_type_for(TypeVariant.DECIMAL)

    assert decimals.accepts_all(["1.00", "2.00"])
    assert not decimals.accepts_all(["1.00", 2.0])
