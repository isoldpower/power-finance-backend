"""The only generator today. No model is wired, on purpose."""

from ..contracts import ConnectionContext
from ..generators import EchoReplyGenerator
from ..generators.echo_generator import REPLY_TEMPLATE

CONTEXT = ConnectionContext(path="/api/v1/chat/advice", external_id="clerk_7")


async def _reply(generator: EchoReplyGenerator, prompt: str) -> list[str]:
    return [increment async for increment in generator.generate(prompt, CONTEXT)]


async def test_the_reply_echoes_the_prompt():
    increments = await _reply(EchoReplyGenerator(), "Why is my dining spend up?")

    assert "".join(increments) == "Received message: Why is my dining spend up?"


async def test_the_template_is_the_one_the_reply_is_built_from():
    """Spelled out here so a change to the canned answer is a change to a test
    rather than a silent change to what every user sees."""

    assert REPLY_TEMPLATE == "Received message: {text}"


async def test_the_reply_arrives_in_several_increments():
    """A single-chunk reply would never exercise a client that concatenates
    deltas, which is the thing this socket exists to prove out."""

    increments = await _reply(EchoReplyGenerator(chunk_words=2), "one two three four five")

    assert len(increments) > 1


async def test_concatenating_the_increments_reproduces_the_reply_exactly():
    """Whitespace included: a split that dropped a space would be invisible in
    a chunk count and obvious on screen."""

    prompt = "a b c d e f g h i"

    for chunk_words in (1, 2, 3, 7):
        increments = await _reply(EchoReplyGenerator(chunk_words=chunk_words), prompt)
        assert "".join(increments) == REPLY_TEMPLATE.format(text=prompt)


async def test_a_nonsensical_chunk_size_still_produces_the_reply():
    increments = await _reply(EchoReplyGenerator(chunk_words=0), "hello there")

    assert "".join(increments) == "Received message: hello there"


async def test_an_empty_prompt_still_answers():
    increments = await _reply(EchoReplyGenerator(), "")

    assert "".join(increments) == "Received message: "
