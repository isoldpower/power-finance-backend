local redis = require "resty.redis"

local plugin_config = require "kong.plugins.write-ral-version.config"



--- Open a connection to Redis using values from the plugin config.
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
    local ok, keepalive_error = client:set_keepalive(
            plugin_config.RedisConnection.KEEPALIVE_TIMEOUT_MS,
            plugin_config.RedisConnection.KEEPALIVE_POOL_SIZE
    )

    if not ok then
        kong.log.warn("write-ral-version: redis keepalive failed: ", keepalive_error)
    end
end


--- Atomically store an offset for a user only if it is greater than
--- the existing value.
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

    local prefix = config.redis_key_prefix or plugin_config.RedisConnection.DEFAULT_KEY_PREFIX
    local key = prefix .. user_id
    local ttl = config.redis_ttl_seconds or plugin_config.RedisConnection.DEFAULT_TTL_SECONDS

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
