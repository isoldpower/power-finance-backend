local sandbox_resolver = require "kong.plugins.sandbox-router.sandbox_resolver"
local sandbox_lookup   = require "kong.plugins.sandbox-router.sandbox_lookup"
local logger_shortcuts = require "kong.plugins.sandbox-router.logger_shortcuts"

local SandboxRouterHandler = {
    PRIORITY = 750,
    VERSION  = "0.2.0",
}


--- Re-point the upstream at a sandbox's own instance of the matched service.
--
-- Every failure below routes to the baseline instead of refusing the request:
-- an unreachable Redis or a half-registered sandbox must not take the gateway
-- down for everyone.
function SandboxRouterHandler:access(config)
    local resolved = sandbox_resolver.resolve_sandbox()
    if not resolved.sandbox_id then
        return
    end

    if config.propagate_baggage and not resolved.from_baggage then
        sandbox_resolver.propagate_sandbox_baggage(
            resolved.baggage_value,
            resolved.sandbox_id
        )
    end

    kong.ctx.shared.sandbox_id = resolved.sandbox_id

    local service_name = sandbox_resolver.resolve_service_name()
    if not service_name then
        logger_shortcuts.log_service_unmatched(resolved.sandbox_id)
        return
    end

    local target, lookup_error = sandbox_lookup.get_sandbox_target(
        config,
        resolved.sandbox_id,
        service_name
    )
    if lookup_error then
        logger_shortcuts.log_lookup_failed(lookup_error)
        return
    end
    if not target then
        logger_shortcuts.log_no_override(resolved.sandbox_id, service_name)
        return
    end

    kong.service.set_target(target.host, target.port)
    logger_shortcuts.log_routed(resolved.sandbox_id, service_name, target)
end


return SandboxRouterHandler
