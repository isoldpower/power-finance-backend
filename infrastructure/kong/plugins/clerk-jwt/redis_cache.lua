local cjson = require "cjson.safe"
local redis = require "resty.redis"


local DEFAULT_KEY_PREFIX  = "clerk:jwks:"
local KEEPALIVE_TIMEOUT_MS = 60000
local KEEPALIVE_POOL_SIZE  = 100


--- Build the per-issuer Redis key. JWKS documents are issuer-scoped,
-- so multiple clerk-jwt instances (e.g. staging + prod) sharing the
-- same Redis never collide on the cache.
--
-- @param config table  plugin config record
-- @return string  fully-qualified Redis key
local build_key = function(config)
    local prefix = config.redis_key_prefix or DEFAULT_KEY_PREFIX
    return prefix .. config.issuer_url
end


--- Open a connection to Redis using values from the plugin config.
-- Selects database and authenticates when configured. On any failure
-- the caller is expected to fall through to a fresh JWKS HTTP fetch
-- rather than 401 the request.
--
-- @param config table  plugin config record
-- @return table|nil  resty.redis client on success
-- @return string|nil  error message on failure
local connect_to_redis = function(config)
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
-- subsequent requests. Avoids a TCP handshake per auth check.
--
-- @param client table  resty.redis client previously returned by `connect_to_redis`
local release = function(client)
    local success, keepalive_error = client:set_keepalive(KEEPALIVE_TIMEOUT_MS, KEEPALIVE_POOL_SIZE)
    if not success then
        kong.log.warn("clerk-jwt cache: redis keepalive failed: ", keepalive_error)
    end
end


--- Read the cached JWKS document from Redis.
-- Returns nil for any "no cache" state (miss, malformed value,
-- connection failure) so the caller can transparently fall through to
-- a fresh HTTP fetch. Connection failures are logged but otherwise
-- not surfaced — the request proceeds.
--
-- @param config table  plugin config record
-- @return table|nil  the decoded JWKS document, or nil on miss
local get_cache_value = function(config)
    local client, connect_error = connect_to_redis(config)
    if not client then
        kong.log.warn("clerk-jwt cache: ", connect_error)
        return nil
    end

    local raw_value, get_error = client:get(build_key(config))
    if get_error then
        client:close()
        kong.log.warn("clerk-jwt cache: redis get: ", get_error)
        return nil
    elseif not get_error then
        release(client)
    end

    if raw_value == ngx.null or not raw_value then
        return nil
    end

    local decoded, decode_error = cjson.decode(raw_value)
    if not decoded then
        kong.log.warn("clerk-jwt cache: redis value malformed, decode failed: ", decode_error)
        return nil
    end

    return decoded
end


--- Encode and write a JWKS document to Redis with TTL.
-- TTL comes from `config.jwks_ttl_seconds`; after expiry the next
-- `get_cache_value` will return nil and trigger a refetch.
--
-- @param config table  plugin config, must contain `jwks_ttl_seconds`
-- @param fresh_value table  the JWKS document to persist
-- @return boolean|nil  true on success, nil on encode or transport failure
local set_cache_value = function(config, fresh_value)
    local encoded_fresh, encode_error = cjson.encode(fresh_value)
    if not encoded_fresh then
        kong.log.err("clerk-jwt cache: encode failed: ", encode_error)
        return nil
    end

    local client, connect_error = connect_to_redis(config)
    if not client then
        kong.log.warn("clerk-jwt cache: ", connect_error)
        return nil
    end

    local set_ok, set_error = client:set(build_key(config), encoded_fresh, "EX", config.jwks_ttl_seconds)
    if set_error then
        client:close()
        kong.log.warn("clerk-jwt cache: redis set: ", set_error)
        return nil
    elseif not set_error then
        release(client)
    end

    if not set_ok then
        return nil
    end

    return true
end


--- Drop the cached JWKS entry.
-- Called when a token's `kid` is absent from the cached JWKS but the
-- cache was populated — likely indicates issuer key rotation, so the
-- next request will re-fetch.
--
-- @param config table  plugin config record
-- @return boolean|nil  true on success, nil on transport failure
local invalidate_cache = function(config)
    local client, connect_error = connect_to_redis(config)
    if not client then
        kong.log.warn("clerk-jwt cache: ", connect_error)
        return nil
    end

    local _, del_error = client:del(build_key(config))
    if del_error then
        client:close()
        kong.log.warn("clerk-jwt cache: redis del: ", del_error)
        return nil
    elseif not del_error then
        release(client)
    end

    return true
end


local exports = {
    get_cache_value  = get_cache_value,
    set_cache_value  = set_cache_value,
    invalidate_cache = invalidate_cache,
}

return exports
