local redis = require "resty.redis"


local DEFAULT_KEY_PREFIX  = "ral:user:"
local DEFAULT_TTL_SECONDS = 604800
local KEEPALIVE_TIMEOUT_MS = 60000
local KEEPALIVE_POOL_SIZE  = 100


-- Monotonic SET — refuses to lower a stored offset, so concurrent /
-- retried writes from the same user can't roll the value backwards.
-- KEYS[1] = "ral:user:" .. user_id
-- ARGV[1] = new offset (digit string)
-- ARGV[2] = TTL seconds
local MONOTONIC_SET_SCRIPT = [[
    local existing = redis.call('GET', KEYS[1])
    if not existing or tonumber(ARGV[1]) > tonumber(existing) then
        redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
        return 1
    end
    return 0
]]


--- Open a connection to Redis using values from the plugin config.
-- Selects database and authenticates when configured. On any failure
-- the caller is expected to fail open (no offset recorded) rather
-- than disturbing the response that has already been sent.
--
-- @param config table  plugin config record
-- @return table|nil  resty.redis client on success
-- @return string|nil  error message on failure
local connect = function(config)
    local client = redis:new()
    client:set_timeouts(config.redis_timeout_ms, config.redis_timeout_ms, config.redis_timeout_ms)

    local connected, connect_error = client:connect(config.redis_host, config.redis_port)
    if not connected then
        return nil, "redis connect: " .. (connect_error or "Unknown Error")
    end

    if config.redis_password and config.redis_password ~= "" then
        local auth_ok, auth_error = client:auth(config.redis_password)
        if not auth_ok then
            client:close()
            return nil, "redis auth: " .. (auth_error or "Unknown Error")
        end
    end

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
-- subsequent requests. Avoids a TCP handshake per response phase.
--
-- @param client table  resty.redis client previously returned by `connect`
local release = function(client)
    local ok, keepalive_error = client:set_keepalive(KEEPALIVE_TIMEOUT_MS, KEEPALIVE_POOL_SIZE)
    if not ok then
        kong.log.warn("write-ral-version: redis keepalive failed: ", keepalive_error)
    end
end


--- Atomically store an offset for a user only if it is greater than
-- the existing value. Concurrent writes for the same user can never
-- decrease the stored value. The TTL is refreshed on every accepted
-- update so inactive users drop out of Redis automatically.
--
-- Best-effort by design: failures are returned for logging but do
-- not affect the upstream response that has already been sent.
--
-- @param config table  plugin config record
-- @param user_id string  Clerk `sub` claim from the verified JWT
-- @param offset string  digit-only offset string (outbox seq)
-- @return boolean|nil  true on success
-- @return string|nil  error message on failure
local set_user_offset_monotonic = function(config, user_id, offset)
    local client, connect_error = connect(config)
    if not client then
        return nil, connect_error
    end

    local prefix = config.redis_key_prefix or DEFAULT_KEY_PREFIX
    local key = prefix .. user_id
    local ttl = config.redis_ttl_seconds or DEFAULT_TTL_SECONDS

    local _, eval_error = client:eval(MONOTONIC_SET_SCRIPT, 1, key, offset, ttl)
    if eval_error then
        client:close()
        return nil, "redis eval: " .. eval_error
    end

    release(client)
    return true, nil
end


local exports = {
    set_user_offset_monotonic = set_user_offset_monotonic,
}

return exports
