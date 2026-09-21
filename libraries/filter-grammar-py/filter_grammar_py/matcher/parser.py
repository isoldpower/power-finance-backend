from typing import Any

from ..entities import FilterPolicy
from ..shapes import GroupShape, LeafShape, shape_of
from .node import MatchNode
from .nodes import AlwaysNode, GroupNode, LeafNode


def build_root(raw: Any, policy: FilterPolicy, path: str) -> MatchNode:
    if raw is None:
        return AlwaysNode()

    return build_node(raw, policy, path)


def build_node(raw: Any, policy: FilterPolicy, path: str) -> MatchNode:
    match shape_of(raw, path):
        case GroupShape(operator=operator, children=children):
            return GroupNode(
                operator,
                [
                    build_node(child, policy, f"{path}.{operator}[{index}]")
                    for index, child in enumerate(children)
                ],
            )
        case LeafShape() as leaf:
            return LeafNode.build(leaf, policy, path)
