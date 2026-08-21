-- Shared response envelope for gateway-terminated requests.
local ISO_8601_UTC = "!%Y-%m-%dT%H:%M:%S+00:00"


--- Correlation id for `meta.request_id`.
local function request_id()
    return kong.request.get_header("X-Correlation-ID") or ngx.null
end

--- Build the standard error envelope body.
-- @param code string  contract `error.code`, e.g. "unauthorized"
-- @param message string  human-readable, safe to log, not for rendering verbatim
local function error_body(code, message)
    return {
        error = {
            code = code,
            message = message,
        },
        meta = {
            request_id = request_id(),
            timestamp = os.date(ISO_8601_UTC),
        },
    }
end

--- Terminate the request with the standard error envelope.
-- @param status number  HTTP status
-- @param code string  contract `error.code`
-- @param message string  human-readable message
-- @param headers table|nil  extra response headers (e.g. Retry-After)
local function exit(status, code, message, headers)
    return kong.response.exit(status, error_body(code, message), headers)
end


return {
    error_body = error_body,
    exit       = exit,
}
