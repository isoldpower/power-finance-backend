from ..application.contracts import ConnectionContext
from ..application.generators import REPLY_TEMPLATE, EchoReplyGenerator

CONTEXT = ConnectionContext(path="/api/v1/chat/advice", external_id="clerk_7")


async def _reply(generator: EchoReplyGenerator, prompt: str) -> list[str]:
    return [increment async for increment in generator.generate(prompt, CONTEXT)]


async def test_the_reply_echoes_the_prompt():
    increments = await _reply(EchoReplyGenerator(), "Why is my dining spend up?")

    assert "".join(increments) == "Received message: Why is my dining spend up?"


async def test_the_template_is_the_one_the_reply_is_built_from():
    assert REPLY_TEMPLATE == "Received message: {text}"


async def test_the_reply_arrives_in_several_increments():
    increments = await _reply(EchoReplyGenerator(chunk_words=2), "one two three four five")

    assert len(increments) > 1


async def test_concatenating_the_increments_reproduces_the_reply_exactly():
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
