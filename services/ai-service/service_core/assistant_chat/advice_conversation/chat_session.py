import asyncio
from contextlib import suppress
from typing import cast

from service_core.shared.logging import get_service_logger

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

logger = get_service_logger("assistant_chat")


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

            received_signal, is_received = await self._receive_or_terminate()
            if not is_received:
                return cast(Termination, received_signal)

            try:
                routed_replies = await self._router.route(
                    cast(dict, received_signal),
                    self._context,
                )

                if not routed_replies.claimed:
                    return Termination.unroutable_message()

                async for frame in routed_replies.frames:
                    await self._transport.send(frame)
            except ClientDisconnectedError:
                return Termination.client_disconnected()
            except Exception:
                logger.exception("chat handler failed while answering")
                return Termination.handler_failed()

    async def _receive_or_terminate(self) -> tuple[dict | Termination, bool]:
        receiving = asyncio.ensure_future(self._transport.receive())
        terminating = asyncio.ensure_future(self._signal.wait())

        try:
            await asyncio.wait(
                {receiving, terminating},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if not receiving.done():
                return terminating.result(), False

            try:
                return receiving.result(), True
            except ClientDisconnectedError:
                return Termination.client_disconnected(), False
            except MalformedFrameError:
                return Termination.malformed_message(), False
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
