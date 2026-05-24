-- Centralised error response builders for the user-tier-rate-limit plugin.
--
-- Each helper calls `kong.response.exit`, which terminates the
-- request immediately — callers should `return messages.X()` so the
-- access phase short-circuits cleanly without further processing.


--- 429 response when the authenticated user has exhausted their
-- per-minute or per-hour budget. The window the request actually
-- tripped is reflected in the `X-RateLimit-Remaining-*` headers set
-- by the handler before this exit, so clients can tell which window
-- they need to back off on.
local rate_limit_exceeded = function()
    return kong.response.exit(429, {
        message = "API rate limit exceeded for this user.",
    })
end


local exports = {
    rate_limit_exceeded = rate_limit_exceeded,
}

return exports
