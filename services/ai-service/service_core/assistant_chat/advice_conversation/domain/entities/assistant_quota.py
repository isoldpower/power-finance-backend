from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssistantQuota:
    allowance: int
    consumed: int

    @property
    def remaining(self) -> int:
        return max(0, self.allowance - self.consumed)

    @property
    def is_exhausted(self) -> bool:
        return self.remaining == 0
