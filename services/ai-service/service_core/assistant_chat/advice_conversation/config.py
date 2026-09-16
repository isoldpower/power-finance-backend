PROMPT_FIELD = "text"
GENERATION_FAILED = "assistant_unavailable"
GENERATION_FAILED_MESSAGE = "The assistant could not finish this reply."
QUOTA_EXHAUSTED = "assistant_quota_exhausted"
QUOTA_EXHAUSTED_MESSAGE = "You have used every assistant message included in your plan."

# The allowance a user is granted the first time they send a message. Raising it
# does not touch anyone already granted one: an existing row keeps the allowance it
# was written with, so a change here applies to new users until a grant is issued.
DEFAULT_MESSAGE_ALLOWANCE = 10

WEBSOCKET_PROTOCOL_HEADER = "Sec-WebSocket-Protocol"
WEBSOCKET_SUBPROTOCOL = "clerk"
