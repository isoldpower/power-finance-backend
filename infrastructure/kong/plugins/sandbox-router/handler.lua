local plugin_config   = require "kong.plugins.sandbox-router.config"
local baggage_parser  = require "kong.plugins.sandbox-router.baggage_parser"
local sandbox_lookup  = require "kong.plugins.sandbox-router.sandbox_lookup"

local SandboxRouterHandler = {
    PRIORITY = 750,
    VERSION  = "0.2.0",
}


local resolve_service_name = function()
    local matched_service = kong.router.get_service()
    if not matched_service then
        return nil
    end

    return matched_service.name
end


local resolve_sandbox_id = function()
    local baggage_header_value = kong.request.get_header(plugin_config.BaggageHeader)
    local baggage_sandbox_id = baggage_parser.read_entry(
        baggage_header_value,
        plugin_config.SandboxBaggageEntry
    )
    if baggage_sandbox_id then
        return baggage_sandbox_id, baggage_header_value, true
    end

    local header_sandbox_id = kong.request.get_header(plugin_config.SandboxHeader)
    if header_sandbox_id and header_sandbox_id ~= "" then
        return header_sandbox_id, baggage_header_value, false
    end

    -- Last, because a URL is the weakest claim of the three: baggage is a decision
    -- already taken upstream and a header is set by a client that could also have set
    -- the URL. Repeating the argument yields a table, and picking the first keeps a
    -- doubled query string from resolving to a Lua table used as a sandbox name.
    local query_sandbox_id = kong.request.get_query_arg(plugin_config.SandboxQueryArgument)
    if type(query_sandbox_id) == "table" then
        query_sandbox_id = query_sandbox_id[1]
    end
    if type(query_sandbox_id) == "string" and query_sandbox_id ~= "" then
        return query_sandbox_id, baggage_header_value, false
    end

    return nil, baggage_header_value, false
end


local propagate_sandbox_baggage = function(baggage_header_value, sandbox_id)
    kong.service.request.set_header(
        plugin_config.BaggageHeader,
        baggage_parser.append_entry(
            baggage_header_value,
            plugin_config.SandboxBaggageEntry,
            sandbox_id
        )
    )
end


function SandboxRouterHandler:access(config)
    local sandbox_id, baggage_header_value, is_in_baggage = resolve_sandbox_id()
    if not sandbox_id then
        return
    end

    if config.propagate_baggage and not is_in_baggage then
        propagate_sandbox_baggage(baggage_header_value, sandbox_id)
    end

    -- Published for plugins that forward requests themselves instead of letting
    -- Kong proxy to the target set below; read-fallback is one.
    kong.ctx.shared.sandbox_id = sandbox_id

    local service_name = resolve_service_name()
    if not service_name then
        kong.log.warn(
            "sandbox-router: request matched no service, cannot scope the route for '",
            sandbox_id,
            "'"
        )
        return
    end

    local target, lookup_error = sandbox_lookup.get_sandbox_target(
        config,
        sandbox_id,
        service_name
    )
    if lookup_error then
        kong.log.warn(
            "sandbox-router: redis lookup failed (routing to baseline): ",
            lookup_error
        )
        return
    end
    if not target then
        kong.log.debug(
            "sandbox-router: sandbox '",
            sandbox_id,
            "' has no override for service '",
            service_name,
            "' (routing to baseline)"
        )
        return
    end

    kong.service.set_target(target.host, target.port)
    kong.log.debug(
        "sandbox-router: routed sandbox '",
        sandbox_id,
        "' service '",
        service_name,
        "' to ",
        target.host,
        ":",
        target.port
    )
end


return SandboxRouterHandler
