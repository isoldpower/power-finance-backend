"""Wire-level constants for the advice conversation."""

PROMPT_FIELD = "text"
GENERATION_FAILED = "assistant_unavailable"
GENERATION_FAILED_MESSAGE = "The assistant could not finish this reply."
QUOTA_EXHAUSTED = "assistant_quota_exhausted"
QUOTA_EXHAUSTED_MESSAGE = "You have used every assistant message included in your plan."

DEFAULT_MESSAGE_ALLOWANCE = 10

WEBSOCKET_PROTOCOL_HEADER = "Sec-WebSocket-Protocol"
WEBSOCKET_SUBPROTOCOL = "clerk"
