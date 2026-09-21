from collections.abc import AsyncIterator

from ..contracts import ConnectionContext, ReplyGenerator

REPLY_TEMPLATE = "Received message: {text}"


class EchoReplyGenerator(ReplyGenerator):
    def __init__(self, chunk_words: int = 4) -> None:
        self._chunk_words = max(1, chunk_words)

    async def generate(
        self,
        prompt: str,
        context: ConnectionContext,
    ) -> AsyncIterator[str]:
        for chunk in _chunked(REPLY_TEMPLATE.format(text=prompt), self._chunk_words):
            yield chunk


def _chunked(reply: str, chunk_words: int) -> list[str]:
    words = reply.split(" ")
    chunks = [" ".join(words[at : at + chunk_words]) for at in range(0, len(words), chunk_words)]

    return [chunk if index == 0 else f" {chunk}" for index, chunk in enumerate(chunks)]
