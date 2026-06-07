from saga_pattern_py import SagaStep


class _Noop(SagaStep[None]):
    async def forward(self) -> None:
        return None

    async def compensate(self) -> None:
        return None


def test_default_name_is_the_class_name():
    assert _Noop().name == "_Noop"
