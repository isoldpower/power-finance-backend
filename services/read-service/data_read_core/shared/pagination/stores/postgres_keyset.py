from functools import reduce
from operator import or_
from typing import Any

from django.db.models import Q, QuerySet

from ..ordering import SortOrder
from ..page_request import PageRequest


def keyset_predicate(read_order: SortOrder, anchor: list[Any]) -> Q:
    """Rows lying past the anchor in the order the store walks in."""

    comparisons: list[Q] = []
    preceding_equal = Q()

    for key, value in zip(read_order.keys, anchor, strict=True):
        comparisons.append(preceding_equal & Q(**{key.keyset_lookup_path: value}))
        preceding_equal = preceding_equal & Q(**{key.field: value})

    return reduce(or_, comparisons)


def apply_keyset(queryset: QuerySet, request: PageRequest) -> QuerySet:
    """Anchor, order and slice a queryset for one page (plus the lookahead row)."""

    read_order = request.read_order
    anchor = request.anchor

    if anchor is not None:
        queryset = queryset.filter(keyset_predicate(read_order, anchor))

    return queryset.order_by(*read_order.django_ordering)[: request.fetch_size]
