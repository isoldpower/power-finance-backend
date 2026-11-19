"""Global categories must carry the same ids and names on both sides.

They are never announced over Kafka: each service seeds them from its own migration
and derives every id from one namespace. A wallet or transaction event that names a
global category by id is only resolvable on the read side if both migrations agree.
"""

import pytest

from ..global_categories import (
    CATALOGUE_NAMES,
    CATALOGUE_SOURCES,
    NAMESPACE_SOURCES,
    module_constants,
)


@pytest.mark.parametrize("catalogue_name", CATALOGUE_NAMES)
def test_both_migrations_seed_the_same_global_categories(catalogue_name):
    catalogues = {
        source: module_constants(path)[catalogue_name] for source, path in CATALOGUE_SOURCES.items()
    }

    assert len(set(map(tuple, catalogues.values()))) == 1, catalogues


def test_every_copy_of_the_id_namespace_agrees():
    namespaces = {
        source: module_constants(path)["GLOBAL_CATEGORY_NAMESPACE"]
        for source, path in NAMESPACE_SOURCES.items()
    }

    assert len(set(namespaces.values())) == 1, namespaces
