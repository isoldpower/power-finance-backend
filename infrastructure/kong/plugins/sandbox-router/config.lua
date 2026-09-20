local BAGGAGE_HEADER_NAME = "baggage"
local SANDBOX_HEADER_NAME = "X-Sandbox"
local SANDBOX_BAGGAGE_ENTRY_NAME = "sandbox-id"
local SANDBOX_QUERY_ARGUMENT_NAME = "sandbox"
local DEFAULT_REDIS_KEY_PREFIX = "sandbox:route:"


return {
    BaggageHeader        = BAGGAGE_HEADER_NAME,
    SandboxHeader        = SANDBOX_HEADER_NAME,
    SandboxBaggageEntry  = SANDBOX_BAGGAGE_ENTRY_NAME,
    SandboxQueryArgument = SANDBOX_QUERY_ARGUMENT_NAME,
    DefaultKeyPrefix     = DEFAULT_REDIS_KEY_PREFIX,
}
