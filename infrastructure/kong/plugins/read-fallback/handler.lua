-- Custom Kong plugin: read-fallback
--
-- Transparent read-your-writes fallback. Attached to the Read Service
-- route, it proxies each read itself and, when the Read Service answers
-- `fallback_status` (507 — its projection is behind the client's
-- Read-At-Least), re-issues the request against the Write Service's
-- always-consistent fallback-read endpoint and returns that instead. The
-- client sees one response and never the 507.
--
-- PRIORITY 650 keeps this BELOW clerk-jwt (801) and read-at-least (700)
-- so the verified `X-User-Id` and the resolved `Read-At-Least` header are
-- already on the request before we forward it.

local forwarder = require "kong.plugins.read-fallback.request_forwarder"
local messages  = require "kong.plugins.read-fallback.messages"
local utilities = require "kong.plugins.read-fallback.utilities"

local ReadFallbackHandler = {
    PRIORITY = 650,
    VERSION  = "0.1.0",
}


function ReadFallbackHandler:access(config)
    if kong.request.get_method() ~= "GET" then
        return
    end

    local path = kong.request.get_path()
    local query = kong.request.get_raw_query()

    local primary, primary_error = forwarder.send(
        config.read_service_url, path, query, config.read_timeout_ms
    )
    if not primary then
        kong.log.err("read-fallback: read-service request failed: ", primary_error)
        return messages.upstream_unreachable("Read Service")
    end

    if primary.status ~= config.fallback_status then
        return forwarder.respond(primary)
    end

    local fallback_path = utilities.build_fallback_path(
        path, config.read_path_prefix, config.fallback_path_prefix
    )
    if not fallback_path then
        kong.log.err("read-fallback: cannot map path '", path,
            "' onto prefix '", config.read_path_prefix,
            "'; returning Read Service ", config.fallback_status)

        return forwarder.respond(primary)
    end

    kong.log.info("read-fallback: read-service returned ", config.fallback_status,
        "; falling back to write-service for ", fallback_path)

    local fallback, fallback_error = forwarder.send(
        config.write_service_url, fallback_path, query, config.fallback_timeout_ms
    )
    if not fallback then
        kong.log.err("read-fallback: write-service fallback failed: ", fallback_error)
        return messages.upstream_unreachable("Write Service fallback")
    end

    return forwarder.respond(fallback)
end


return ReadFallbackHandler
