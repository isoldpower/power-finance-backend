local redis = require "resty.redis"


local DEFAULT_KEY_PREFIX  = "ral:user:"
local KEEPALIVE_TIMEOUT_MS = 60000
local KEEPALIVE_POOL_SIZE  = 100


-- The write side of this contract lives in the `write-ral-version` plugin
-- (write-ral-version/redis_writer.lua). It performs a monotonic Lua SET
-- on the same keys this module GETs from.


--- Open a connection to Redis using values from the plugin config.
-- Selects database and authenticates when configured. On any failure
-- the caller is expected to fail open (no header injected) rather
-- than 503 the read path.
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
-- @param client table  resty.redis client previously returned by `connect`
local release = function(client)
    local ok, keepalive_error = client:set_keepalive(KEEPALIVE_TIMEOUT_MS, KEEPALIVE_POOL_SIZE)
    if not ok then
        kong.log.warn("read-at-least: redis keepalive failed: ", keepalive_error)
    end
end


--- Look up the latest stored offset for a user.
-- Returns nil for any "no offset known" state (cache miss, malformed
-- value, connection failure) so the caller can fail open uniformly.
-- Connection failures and corrupt values are surfaced as the second
-- return value purely for logging — the request still proceeds.
--
-- @param config table  plugin config record
-- @param user_id string  Clerk `sub` claim from the verified JWT
-- @return string|nil  offset as a digit-only string, or nil on miss
-- @return string|nil  error message when something went wrong (for logging)
local get_user_offset = function(config, user_id)
    local client, connect_error = connect_to_redis(config)
    if not client then
        return nil, connect_error
    end

    local final_prefix = config.redis_key_prefix or DEFAULT_KEY_PREFIX
    local key = final_prefix .. user_id
    local raw_value, get_error = client:get(key)
    if get_error then
        client:close()

        return nil, "redis get: " .. get_error
    elseif not get_error then
        release(client)
    end

    if raw_value == ngx.null or not raw_value then
        return nil, nil
    elseif type(raw_value) ~= "string" or not raw_value:match("^%d+$") then
        return nil, "redis value malformed: " .. tostring(raw_value)
    end

    return raw_value, nil
end


local exports = {
    get_user_offset = get_user_offset,
}

return exports
