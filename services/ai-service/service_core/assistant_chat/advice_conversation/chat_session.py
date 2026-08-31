import asyncio
from contextlib import suppress

from .contracts import (
    ChatTransport,
    ConnectionContext,
    Termination,
    TerminationSignal,
)
from .exceptions import (
    ClientDisconnectedError,
    MalformedFrameError,
)
from .message_router import MessageRouter


class ChatSession:
    def __init__(
        self,
        transport: ChatTransport,
        router: MessageRouter,
        termination_signal: TerminationSignal,
        context: ConnectionContext,
    ) -> None:
        self._transport = transport
        self._router = router
        self._signal = termination_signal
        self._context = context

    async def run(self) -> Termination:
        termination = await self._start_converse()
        if termination.announced:
            await self._transport.close(termination)

        return termination

    async def _start_converse(self) -> Termination:
        while True:
            if self._signal.is_terminated():
                return await self._signal.wait()

            received = await self._receive_or_terminate()
            if isinstance(received, Termination):
                return received

            try:
                routed = await self._router.route(received, self._context)
            except ClientDisconnectedError:
                return Termination.client_disconnected()

            if not routed.claimed:
                return Termination.unroutable_message()

            try:
                for reply in routed.replies:
                    await self._transport.send(reply)
            except ClientDisconnectedError:
                return Termination.client_disconnected()

    async def _receive_or_terminate(self) -> dict | Termination:
        receiving = asyncio.ensure_future(self._transport.receive())
        terminating = asyncio.ensure_future(self._signal.wait())

        try:
            await asyncio.wait(
                {receiving, terminating},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if not receiving.done():
                return terminating.result()

            try:
                return receiving.result()
            except ClientDisconnectedError:
                return Termination.client_disconnected()
            except MalformedFrameError:
                return Termination.malformed_message()
        finally:
            await _settle_task(terminating)
            await _settle_task(receiving)


async def _settle_task(task: asyncio.Task) -> None:
    if not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        return

    if not task.cancelled():
        task.exception()
