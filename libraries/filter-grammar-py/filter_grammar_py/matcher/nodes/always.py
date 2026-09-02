from ..node import MatchNode, Record


class AlwaysNode(MatchNode):
    def matches(self, record: Record) -> bool:
        return True
