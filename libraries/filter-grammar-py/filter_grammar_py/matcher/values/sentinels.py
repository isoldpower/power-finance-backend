class NeverEqual:
    def __eq__(self, other: object) -> bool:
        return False

    def __hash__(self) -> int:
        return id(self)


NEVER_EQUAL = NeverEqual()
