-- Centralised error response builders for the user-tier-rate-limit plugin.

local envelope = require "power_finance.envelope"


--- 429 when the authenticated user has exhausted their per-minute or
-- per-hour budget.
--
-- `Retry-After` carries the seconds left in the window that actually
-- tripped, so a client backs off for exactly as long as it has to
-- rather than guessing. The window is also visible in the
-- `X-RateLimit-Remaining-*` headers the handler set before this exit.
--
-- @param retry_after number  seconds until the tripped window resets
local rate_limit_exceeded = function(retry_after)
    return envelope.exit(
        429,
        "rate_limited",
        "API rate limit exceeded for this user.",
        { ["Retry-After"] = tostring(retry_after) }
    )
end


local exports = {
    rate_limit_exceeded = rate_limit_exceeded,
}

return exports
