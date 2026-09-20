--- Log lines emitted by the sandbox-router plugin.
--
-- The plugin fails open on every error, so a log line is the only trace a
-- request that quietly went to the baseline leaves behind. Keeping them here
-- keeps the wording stable across the three places routing can stop.


local LOG_PREFIX = "sandbox-router: "


--- The request matched no Kong service, so there is nothing to re-point.
--
-- @param sandbox_id string  the sandbox that asked for an override
local log_service_unmatched = function(sandbox_id)
    kong.log.warn(
        LOG_PREFIX,
        "request matched no service, cannot scope the route for '",
        sandbox_id,
        "'"
    )
end


--- Redis could not be read; the request falls through to the baseline.
--
-- @param lookup_error string  message from the lookup
local log_lookup_failed = function(lookup_error)
    kong.log.warn(
        LOG_PREFIX,
        "redis lookup failed (routing to baseline): ",
        lookup_error
    )
end


--- The sandbox exists but has not overridden this service.
--
-- @param sandbox_id string
-- @param service_name string  the Kong service the request matched
local log_no_override = function(sandbox_id, service_name)
    kong.log.debug(
        LOG_PREFIX,
        "sandbox '",
        sandbox_id,
        "' has no override for service '",
        service_name,
        "' (routing to baseline)"
    )
end


--- The upstream was re-pointed at the sandbox's target.
--
-- @param sandbox_id string
-- @param service_name string
-- @param target table  { host = string, port = number }
local log_routed = function(sandbox_id, service_name, target)
    kong.log.debug(
        LOG_PREFIX,
        "routed sandbox '",
        sandbox_id,
        "' service '",
        service_name,
        "' to ",
        target.host,
        ":",
        target.port
    )
end


local exports = {
    log_service_unmatched = log_service_unmatched,
    log_lookup_failed     = log_lookup_failed,
    log_no_override       = log_no_override,
    log_routed            = log_routed,
}

return exports
