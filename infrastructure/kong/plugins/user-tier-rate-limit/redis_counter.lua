local redis = require "resty.redis"


local KEEPALIVE_TIMEOUT_MS = 60000
local KEEPALIVE_POOL_SIZE  = 100


--- Open a connection to Redis using values from the plugin config.
-- Selects database and authenticates when configured. On any failure
-- the caller is expected to fail open (no counters touched, no
-- headers set) rather than 503 the request path.
--
-- @param config table  plugin config record
-- @return table|nil  resty.redis client on success
-- @return string|nil  error message on failure
local connect_to_redis = function(config)
    local client = redis:new()
    client:set_timeouts(config.redis_timeout_ms, config.redis_timeout_ms, config.redis_timeout_ms)

    -- Establish initial connection.
    local connected, connect_error = client:connect(config.redis_host, config.redis_port)
    if not connected then
        return nil, "redis connect: " .. (connect_error or "Unknown Error")
    end

    -- Try authenticate using provided password.
    if config.redis_password and config.redis_password ~= "" then
        local auth_ok, auth_error = client:auth(config.redis_password)
        if not auth_ok then
            client:close()
            return nil, "redis auth: " .. (auth_error or "Unknown Error")
        end
    end

    -- Check if database is alive by making test request.
    if config.redis_database and config.redis_database > 0 then
        local select_ok, select_error = client:select(config.redis_database)
        if not select_ok then
            client:close()
            return nil, "redis select db: " .. (select_error or "Unknown Error")
        end
    end

    return client, nil
end


--- Return the Redis client to the keepalive pool for reuse on
-- subsequent requests. Avoids a TCP handshake per access phase.
--
-- @param client table  resty.redis client previously returned by `connect_to_redis`
local release = function(client)
    local success, keepalive_error = client:set_keepalive(KEEPALIVE_TIMEOUT_MS, KEEPALIVE_POOL_SIZE)
    if not success then
        kong.log.warn("user-tier-rate-limit: redis keepalive failed: ", keepalive_error)
    end
end


--- Increment the counter for one (user, window) bucket and return
-- the post-increment count.
--
-- Window-key format: `{key_prefix}{user_id}:{window_label}:{bucket}`,
-- where bucket is the aligned epoch (floor(now / window_seconds)) so
-- every worker process and Kong instance counts against the same key.
-- The EXPIRE is set only on the first increment for the bucket, so
-- the window slides forward cleanly without per-request TTL churn.
--
-- @param client table  resty.redis client
-- @param key_prefix string  user-id key prefix (e.g. "rl:user:")
-- @param user_id string  Clerk `sub` claim
-- @param window_label string  human label appended to key ("minute" / "hour")
-- @param window_seconds number  size of the fixed window in seconds
-- @return number|nil  post-increment count
-- @return string|nil  error message on failure
local increment_window = function(client, key_prefix, user_id, window_label, window_seconds)
    local bucket = math.floor(ngx.time() / window_seconds)
    local key = key_prefix .. user_id .. ":" .. window_label .. ":" .. bucket

    local count, incr_error = client:incr(key)
    if not count then
        return nil, "redis incr: " .. (incr_error or "Unknown Error")
    end

    if count == 1 then
        local _, expire_error = client:expire(key, window_seconds)
        if expire_error then
            kong.log.warn("user-tier-rate-limit: redis expire: ", expire_error)
        end
    end

    return count, nil
end


local exports = {
    connect_to_redis = connect_to_redis,
    release          = release,
    increment_window = increment_window,
}

return exports
