local messages      = require "kong.plugins.user-tier-rate-limit.messages"
local redis_counter = require "kong.plugins.user-tier-rate-limit.redis_counter"
local plugin_config = require "kong.plugins.user-tier-rate-limit.config"
local retry_after   = require "kong.plugins.user-tier-rate-limit.retry_after"

local UserTierRateLimitHandler = {
    PRIORITY = 600,
    VERSION  = "0.3.0",
}


--- Set the `X-RateLimit-{Limit,Remaining}-{window}` response headers.
--
-- @param evaluated_window table  one row of the counter's reply
local set_window_headers = function(evaluated_window)
    local remaining = evaluated_window.limit - evaluated_window.estimate

    kong.response.set_header(
        "X-RateLimit-Limit-" .. evaluated_window.header_suffix,
        evaluated_window.limit
    )
    kong.response.set_header(
        "X-RateLimit-Remaining-" .. evaluated_window.header_suffix,
        math.max(0, remaining)
    )
end


function UserTierRateLimitHandler:access(config)
    local claims = kong.ctx.shared.clerk_claims
    if not claims or not claims.sub or claims.sub == "" then
        return
    end

    local client, connect_error = redis_counter.connect_to_redis(config)
    if not client then
        kong.log.warn("user-tier-rate-limit: ", connect_error, " — failing open")
        return
    end

    local evaluated, evaluate_error = redis_counter.evaluate_windows(
        client, config, claims.sub, plugin_config.LimitingWindows
    )
    redis_counter.release(client)

    if not evaluated then
        kong.log.warn("user-tier-rate-limit: ", evaluate_error, " — failing open")
        return
    end

    for _, evaluated_window in ipairs(evaluated.windows) do
        set_window_headers(evaluated_window)
    end

    if not evaluated.allowed then
        return messages.rate_limit_exceeded(retry_after.retry_after_seconds(evaluated))
    end
end


return UserTierRateLimitHandler
