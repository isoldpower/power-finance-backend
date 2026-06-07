"""Shared test doubles for saga-pattern-py.

Kept at the project root, importable as ``from fakes import RecordingStep``,
so co-located tests under ``saga_pattern_py/__tests__`` share one double.
"""

from __future__ import annotations

from saga_pattern_py import SagaStep


class RecordingStep(SagaStep[object]):
    """A SagaStep that records every forward/compensate call onto a shared log.

    Pass the same ``log`` list to several steps to assert the exact order in
    which the coordinator drove them. Either phase can be made to fail.
    """

    def __init__(
        self,
        name: str,
        log: list[tuple[str, str]],
        *,
        result: object = None,
        fail_forward: bool = False,
        fail_compensate: bool = False,
    ) -> None:
        self._name = name
        self._log = log
        self._result = result
        self._fail_forward = fail_forward
        self._fail_compensate = fail_compensate

    @property
    def name(self) -> str:
        return self._name

    async def forward(self) -> object:
        self._log.append(("forward", self._name))
        if self._fail_forward:
            raise RuntimeError(f"forward failed: {self._name}")
        return self._result

    async def compensate(self) -> None:
        self._log.append(("compensate", self._name))
        if self._fail_compensate:
            raise RuntimeError(f"compensate failed: {self._name}")
