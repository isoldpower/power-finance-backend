local BAGGAGE_HEADER_NAME = "baggage"
local SANDBOX_HEADER_NAME = "X-Sandbox"
local SANDBOX_BAGGAGE_ENTRY_NAME = "sandbox-id"
-- A browser cannot set headers on a WebSocket handshake: the constructor takes a URL
-- and subprotocols, nothing else. The Clerk token already rides the subprotocol list,
-- and clerk-jwt accepts that list only when it holds exactly two entries, so a third
-- channel is needed rather than a third pair.
local SANDBOX_QUERY_ARGUMENT_NAME = "sandbox"
local DEFAULT_REDIS_KEY_PREFIX = "sandbox:route:"


return {
    BaggageHeader        = BAGGAGE_HEADER_NAME,
    SandboxHeader        = SANDBOX_HEADER_NAME,
    SandboxBaggageEntry  = SANDBOX_BAGGAGE_ENTRY_NAME,
    SandboxQueryArgument = SANDBOX_QUERY_ARGUMENT_NAME,
    DefaultKeyPrefix     = DEFAULT_REDIS_KEY_PREFIX,
}
