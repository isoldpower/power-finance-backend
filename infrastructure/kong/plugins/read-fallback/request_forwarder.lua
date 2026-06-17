-- HTTP forwarding helpers for the read-fallback plugin.

local http   = require "resty.http"
local config = require "kong.plugins.read-fallback.config"


--- Collect the headers to forward upstream.
-- Reads the *current* request headers, which already include everything
-- earlier plugins injected
local collect_request_headers = function()
    local forwarded = {}
    for name, value in pairs(ngx.req.get_headers()) do
        if not config.SKIP_HEADERS[name:lower()] then
            forwarded[name] = value
        end
    end

    return forwarded
end


--- Copy response headers back to the client, dropping hop-by-hop and
-- length/encoding-framing headers so Kong frames the body it re-emits.
local collect_response_headers = function(raw_headers)
    local response_headers = {}
    for name, value in pairs(raw_headers or {}) do
        if not config.SKIP_HEADERS[name:lower()] then
            response_headers[name] = value
        end
    end

    return response_headers
end


--- Issue a GET to `base_url .. path[?query]` forwarding the inbound headers.
--
-- @return table|nil  resty.http response (status, headers, body) on success
-- @return string|nil  error message on transport failure
local send = function(base_url, path, query, timeout_ms)
    local client = http.new()
    client:set_timeout(timeout_ms)

    local url = base_url .. path
    if query and query ~= "" then
        url = url .. "?" .. query
    end

    local response, request_error = client:request_uri(url, {
        method            = "GET",
        headers           = collect_request_headers(),
        keepalive_timeout = config.KEEPALIVE_TIMEOUT_MS,
        keepalive_pool    = config.KEEPALIVE_POOL_SIZE,
    })
    if not response then
        return nil, request_error or "Unknown Error"
    end

    return response
end


--- Return a forwarded upstream response to the client verbatim.
-- Terminates the request — callers should `return forward.respond(...)`.
local respond = function(response)
    return kong.response.exit(
        response.status,
        response.body,
        collect_response_headers(response.headers)
    )
end


return {
    send    = send,
    respond = respond,
}
