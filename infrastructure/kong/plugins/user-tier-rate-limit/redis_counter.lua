local redis = require "resty.redis"
local resty_string = require "resty.string"

local window_script = require "kong.plugins.user-tier-rate-limit.window_script"


local KEEPALIVE_TIMEOUT_MS = 60000
local KEEPALIVE_POOL_SIZE  = 100
local TTL_WINDOWS = 2


local script_sha

--- Digest of the script, computed once per worker.
local script_digest = function()
    if not script_sha then
        script_sha = resty_string.to_hex(ngx.sha1_bin(window_script.REDIS_SCRIPT))
    end

    return script_sha
end


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
    client:set_timeouts(
        config.redis_timeout_ms,
        config.redis_timeout_ms,
        config.redis_timeout_ms
    )
    local connected, connect_error = client:connect(
        config.redis_host,
        config.redis_port
    )
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
-- subsequent requests. Avoids a TCP handshake per access phase.
--
-- @param client table  resty.redis client previously returned by `connect_to_redis`
local release = function(client)
    local success, keepalive_error = client:set_keepalive(
        KEEPALIVE_TIMEOUT_MS,
        KEEPALIVE_POOL_SIZE
    )

    if not success then
        kong.log.warn("user-tier-rate-limit: redis keepalive failed: ", keepalive_error)
    end
end


--- Position of `now` inside a window, and how much of the previous bucket the
-- sliding window still covers.
--
-- @param window table  one row of the handler's WINDOWS table
-- @param now number  wall clock seconds, fractional
-- @return table  bucket ids, elapsed seconds, and the previous bucket's weight
local window_position = function(window, now)
    local bucket = math.floor(now / window.seconds)
    local elapsed = now - bucket * window.seconds

    return {
        current_bucket = bucket,
        previous_bucket = bucket - 1,
        elapsed = elapsed,
        previous_weight = (window.seconds - elapsed) / window.seconds,
    }
end


local bucket_key = function(key_prefix, user_id, window, bucket)
    return key_prefix .. user_id .. ":" .. window.label .. ":" .. bucket
end


--- Run the script, sending its body only when Redis has not cached it.
local run_script = function(client, keys, arguments)
    local call_arguments = { script_digest(), #keys }
    for _, key in ipairs(keys) do
        call_arguments[#call_arguments + 1] = key
    end
    for _, argument in ipairs(arguments) do
        call_arguments[#call_arguments + 1] = argument
    end

    local reply, call_error = client:evalsha(unpack(call_arguments))
    if reply then
        return reply, nil
    end

    if call_error and string.find(call_error, "NOSCRIPT", 1, true) then
        call_arguments[1] = window_script.REDIS_SCRIPT
        return client:eval(unpack(call_arguments))
    end

    return nil, call_error
end


--- Evaluate every window for one user and, if all of them admit the request,
-- count it against all of them.
--
-- @param client table  resty.redis client
-- @param config table  plugin config record
-- @param user_id string  Clerk `sub` claim
-- @param windows table  the handler's WINDOWS table
-- @return table|nil  { allowed = bool, windows = { { label, limit, estimate, ... } } }
-- @return string|nil  error message on failure
local evaluate_windows = function(client, config, user_id, windows)
    local now = ngx.now()
    local keys, arguments, positions = {}, { #windows }, {}

    for index, window in ipairs(windows) do
        local position = window_position(window, now)
        positions[index] = position

        keys[#keys + 1] = bucket_key(
            config.redis_key_prefix,
            user_id,
            window,
            position.current_bucket
        )
        keys[#keys + 1] = bucket_key(
            config.redis_key_prefix,
            user_id,
            window,
            position.previous_bucket
        )

        arguments[#arguments + 1] = config[window.config_key]
        arguments[#arguments + 1] = position.previous_weight
        arguments[#arguments + 1] = window.seconds * TTL_WINDOWS
    end

    local reply, script_error = run_script(client, keys, arguments)
    if not reply then
        return nil, "redis eval: " .. (script_error or "Unknown Error")
    end

    local evaluated = { allowed = tonumber(reply[1]) == 1, windows = {} }

    for index, window in ipairs(windows) do
        local reply_base = 1 + (index - 1) * 3

        evaluated.windows[index] = {
            label = window.label,
            header_suffix = window.header_suffix,
            seconds = window.seconds,
            limit = config[window.config_key],
            previous = tonumber(reply[reply_base + 1]),
            current = tonumber(reply[reply_base + 2]),
            estimate = tonumber(reply[reply_base + 3]),
            elapsed = positions[index].elapsed,
        }
    end

    return evaluated, nil
end


local exports = {
    connect_to_redis = connect_to_redis,
    release          = release,
    evaluate_windows = evaluate_windows,
}

return exports
