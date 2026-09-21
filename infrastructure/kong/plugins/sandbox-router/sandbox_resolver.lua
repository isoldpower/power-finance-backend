local plugin_config  = require "kong.plugins.sandbox-router.config"
local baggage_parser = require "kong.plugins.sandbox-router.baggage_parser"


--- The first value of a query argument Kong may have parsed as a list.
--
-- @param query_argument string|table|nil
-- @return string|nil
local first_query_value = function(query_argument)
    if type(query_argument) == "table" then
        return query_argument[1]
    end

    return query_argument
end


--- Which sandbox this request belongs to, and how it said so.
--
-- The three channels are tried in order of how deliberate they are. Baggage is
-- a decision already taken upstream. A header is set by a client that could
-- equally have written the URL. The query argument is last and exists only
-- because a browser cannot set headers on a WebSocket handshake.
--
-- @return table  {
--   sandbox_id    = string|nil,  nil when the request names no sandbox
--   baggage_value = string|nil,  the inbound baggage header, verbatim
--   from_baggage  = boolean,     true when the id was already in that header
-- }
local resolve_sandbox = function()
    local baggage_value = kong.request.get_header(plugin_config.BaggageHeader)

    local baggage_sandbox_id = baggage_parser.read_entry(
        baggage_value,
        plugin_config.SandboxBaggageEntry
    )
    if baggage_sandbox_id then
        return {
            sandbox_id    = baggage_sandbox_id,
            baggage_value = baggage_value,
            from_baggage  = true,
        }
    end

    local header_sandbox_id = kong.request.get_header(plugin_config.SandboxHeader)
    if header_sandbox_id and header_sandbox_id ~= "" then
        return {
            sandbox_id    = header_sandbox_id,
            baggage_value = baggage_value,
            from_baggage  = false,
        }
    end

    local query_sandbox_id = first_query_value(
        kong.request.get_query_arg(plugin_config.SandboxQueryArgument)
    )
    if type(query_sandbox_id) == "string" and query_sandbox_id ~= "" then
        return {
            sandbox_id    = query_sandbox_id,
            baggage_value = baggage_value,
            from_baggage  = false,
        }
    end

    return {
        sandbox_id    = nil,
        baggage_value = baggage_value,
        from_baggage  = false,
    }
end


--- The name of the Kong service the router matched, if any.
--
-- @return string|nil
local resolve_service_name = function()
    local matched_service = kong.router.get_service()
    if not matched_service then
        return nil
    end

    return matched_service.name
end


--- Add the sandbox id to the outbound baggage header.
--
-- Called when the id arrived some other way, so that downstream services and
-- the Kafka consumers behind them see it on the one carrier they all read.
--
-- @param baggage_value string|nil  the inbound baggage header
-- @param sandbox_id string
local propagate_sandbox_baggage = function(baggage_value, sandbox_id)
    kong.service.request.set_header(
        plugin_config.BaggageHeader,
        baggage_parser.append_entry(
            baggage_value,
            plugin_config.SandboxBaggageEntry,
            sandbox_id
        )
    )
end


local exports = {
    resolve_sandbox           = resolve_sandbox,
    resolve_service_name      = resolve_service_name,
    propagate_sandbox_baggage = propagate_sandbox_baggage,
}

return exports
