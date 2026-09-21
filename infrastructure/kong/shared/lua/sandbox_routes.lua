local redis = require "resty.redis"

local DEFAULT_KEY_PREFIX   = "sandbox:route:"
local KEEPALIVE_TIMEOUT_MS = 60000
local KEEPALIVE_POOL_SIZE  = 100


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


local release = function(client)
    local ok, keepalive_error = client:set_keepalive(KEEPALIVE_TIMEOUT_MS, KEEPALIVE_POOL_SIZE)
    if not ok then
        kong.log.warn("sandbox routes: redis keepalive failed: ", keepalive_error)
    end
end


local parse_upstream_target = function(raw_value)
    local host, port = raw_value:match("^([^:]+):(%d+)$")
    if not host then
        return nil, "redis value malformed: " .. tostring(raw_value)
    end

    return { host = host, port = tonumber(port) }, nil
end


local build_route_key = function(config, sandbox_id, service_name)
    local final_prefix = config.redis_key_prefix or DEFAULT_KEY_PREFIX

    return final_prefix .. sandbox_id .. ":" .. service_name
end


local resolve_target = function(config, sandbox_id, service_name)
    local client, connect_error = connect_to_redis(config)
    if not client then
        return nil, connect_error
    end

    local raw_value, get_error = client:get(build_route_key(config, sandbox_id, service_name))
    if get_error then
        client:close()

        return nil, "redis get: " .. get_error
    end
    release(client)

    if raw_value == ngx.null or not raw_value or type(raw_value) ~= "string" then
        return nil, nil
    end

    return parse_upstream_target(raw_value)
end


local exports = {
    build_route_key = build_route_key,
    resolve_target  = resolve_target,
}

return exports
