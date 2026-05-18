-- Custom Kong plugin: user-tier-rate-limit
--
-- Per-user rate limit applied on top of the IP floor. Runs after clerk-jwt
-- so the verified `sub` claim is available — no claims means the request
-- is anonymous and this plugin is a no-op (the IP floor still applies).
--
-- Why custom: Kong's bundled rate-limiting plugin can only have one
-- instance per scope. We need the IP floor (built-in) AND a per-user
-- ceiling at the same time, so the user tier needs to be a separate
-- plugin class.
--
-- Counter strategy: fixed minute/hour windows in Redis via INCR + EXPIRE.
-- Cheaper and simpler than a sliding window; accuracy at window edges is
-- fine for fraud/abuse prevention.

local redis = require "resty.redis"

local UserTierRateLimitHandler = {
    PRIORITY = 600,
    VERSION  = "0.1.0",
}


local function open_redis(conf)
    local r = redis:new()
    r:set_timeout(conf.redis_timeout_ms or 1000)
    local ok, err = r:connect(conf.redis_host, conf.redis_port)
    if not ok then
        return nil, "redis connect: " .. (err or "unknown")
    end
    if conf.redis_password and conf.redis_password ~= "" then
        local auth_ok, auth_err = r:auth(conf.redis_password)
        if not auth_ok then
            return nil, "redis auth: " .. (auth_err or "unknown")
        end
    end
    if conf.redis_database and conf.redis_database > 0 then
        r:select(conf.redis_database)
    end
    return r
end


local function close_redis(r)
    -- Return to pool instead of closing to amortise TCP setup across
    -- worker requests. 30s idle / 100 max pool size are workable defaults.
    r:set_keepalive(30000, 100)
end


-- Returns the current count after this request and the configured limit.
-- Window-key format is `<prefix>:<user_id>:<bucket>` where bucket is the
-- aligned epoch for the window length, so all worker processes count
-- against the same key.
local function increment_window(r, prefix, user_id, window_seconds, limit)
    local bucket = math.floor(ngx.time() / window_seconds)
    local key = prefix .. ":" .. user_id .. ":" .. bucket
    local count, err = r:incr(key)
    if not count then
        return nil, "redis incr: " .. (err or "unknown")
    end
    if count == 1 then
        r:expire(key, window_seconds)
    end
    return count
end


local function set_window_headers(window, limit, remaining)
    local suffix = window == 60 and "Minute" or "Hour"
    kong.response.set_header("X-RateLimit-Limit-" .. suffix, limit)
    kong.response.set_header("X-RateLimit-Remaining-" .. suffix, math.max(0, remaining))
end


function UserTierRateLimitHandler:access(conf)
    local claims = kong.ctx.shared.clerk_claims
    if not claims or not claims.sub or claims.sub == "" then
        -- Anonymous request — IP floor (built-in rate-limiting plugin) is
        -- the only tier that applies. Skip silently.
        return
    end
    local user_id = claims.sub

    local r, err = open_redis(conf)
    if not r then
        kong.log.warn("user-tier-rate-limit: ", err, " — failing open")
        return
    end

    local minute_limit = conf.per_minute
    local hour_limit   = conf.per_hour

    local minute_count, m_err = increment_window(
        r, "rl:user:minute", user_id, 60, minute_limit
    )
    if not minute_count then
        kong.log.warn("user-tier-rate-limit: ", m_err, " — failing open")
        close_redis(r)
        return
    end

    local hour_count, h_err = increment_window(
        r, "rl:user:hour", user_id, 3600, hour_limit
    )
    if not hour_count then
        kong.log.warn("user-tier-rate-limit: ", h_err, " — failing open")
        close_redis(r)
        return
    end

    close_redis(r)

    set_window_headers(60, minute_limit, minute_limit - minute_count)
    set_window_headers(3600, hour_limit, hour_limit - hour_count)

    if minute_count > minute_limit or hour_count > hour_limit then
        return kong.response.exit(429, {
            message = "API rate limit exceeded for this user.",
        })
    end
end


return UserTierRateLimitHandler
