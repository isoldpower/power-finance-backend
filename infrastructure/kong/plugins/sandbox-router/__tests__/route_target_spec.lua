-- What the handler does with the sandbox id once it has one. The plugin fails
-- open at every step, so each branch below has to leave the upstream untouched
-- and let the request reach the baseline.
local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local headers, query = {}, {}
local matched_service, lookup_result, lookup_error
local set_target_call, outbound_baggage, logged

kong = {
    request = {
        get_header    = function(name) return headers[name] end,
        get_query_arg = function(name) return query[name] end,
    },
    service = {
        set_target = function(host, port) set_target_call = { host = host, port = port } end,
        request = {
            set_header = function(name, value)
                if name == "baggage" then outbound_baggage = value end
            end,
        },
    },
    router = { get_service = function() return matched_service end },
    log = {
        warn  = function() logged = "warn" end,
        debug = function() logged = "debug" end,
        err   = function() logged = "err" end,
    },
    ctx = { shared = {} },
}

package.loaded["kong.plugins.sandbox-router.config"] = dofile(PLUGIN .. "/config.lua")
package.loaded["kong.plugins.sandbox-router.baggage_parser"] =
    dofile(PLUGIN .. "/baggage_parser.lua")
package.loaded["kong.plugins.sandbox-router.sandbox_resolver"] =
    dofile(PLUGIN .. "/sandbox_resolver.lua")
package.loaded["kong.plugins.sandbox-router.logger_shortcuts"] =
    dofile(PLUGIN .. "/logger_shortcuts.lua")
package.loaded["kong.plugins.sandbox-router.sandbox_lookup"] = {
    get_sandbox_target = function() return lookup_result, lookup_error end,
}

local handler = dofile(PLUGIN .. "/handler.lua")

local DEFAULT_CONFIG = { propagate_baggage = true }

local failures = 0
local function report(ok, label, expected, actual)
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local function given(options)
    headers          = options.headers or {}
    query            = options.query or {}
    matched_service  = options.service
    lookup_result    = options.target
    lookup_error     = options.lookup_error
    set_target_call  = nil
    outbound_baggage = nil
    logged           = nil
    kong.ctx.shared  = {}

    handler:access(options.config or DEFAULT_CONFIG)
end

local SANDBOX = { ["X-Sandbox"] = "nikita" }
local SERVICE = { name = "read-service" }
local TARGET = { host = "host.docker.internal", port = 8100 }

given({ service = SERVICE, target = TARGET })
report(set_target_call == nil, "no sandbox id leaves the upstream alone", nil, set_target_call)

given({ headers = SANDBOX, service = SERVICE, target = TARGET })
report(
    set_target_call ~= nil
        and set_target_call.host == TARGET.host
        and set_target_call.port == TARGET.port,
    "a matched override re-points the upstream",
    "host.docker.internal:8100",
    set_target_call and (set_target_call.host .. ":" .. set_target_call.port)
)
report(logged == "debug", "a successful route logs at debug", "debug", logged)

given({ headers = SANDBOX, service = nil, target = TARGET })
report(set_target_call == nil, "no matched service falls through to baseline", nil, set_target_call)
report(logged == "warn", "an unmatched service warns", "warn", logged)

given({ headers = SANDBOX, service = SERVICE, lookup_error = "connection refused" })
report(set_target_call == nil, "a redis failure falls through to baseline", nil, set_target_call)
report(logged == "warn", "a redis failure warns", "warn", logged)

given({ headers = SANDBOX, service = SERVICE, target = nil })
report(set_target_call == nil, "no override for this service keeps baseline", nil, set_target_call)
report(logged == "debug", "a missing override logs at debug", "debug", logged)

given({ headers = SANDBOX, service = SERVICE, target = TARGET })
report(
    kong.ctx.shared.sandbox_id == "nikita",
    "the sandbox id is published on kong.ctx.shared",
    "nikita",
    kong.ctx.shared.sandbox_id
)

given({ headers = SANDBOX, service = SERVICE, target = TARGET })
report(
    outbound_baggage == "sandbox-id=nikita",
    "a header-borne id is added to outbound baggage",
    "sandbox-id=nikita",
    outbound_baggage
)

given({
    headers = { baggage = "team=core", ["X-Sandbox"] = "nikita" },
    service = SERVICE,
    target  = TARGET,
})
report(
    outbound_baggage == "team=core,sandbox-id=nikita",
    "existing baggage entries are preserved",
    "team=core,sandbox-id=nikita",
    outbound_baggage
)

given({ headers = { baggage = "sandbox-id=nikita" }, service = SERVICE, target = TARGET })
report(
    outbound_baggage == nil,
    "an id already in baggage is not written again",
    nil,
    outbound_baggage
)

given({
    headers = SANDBOX,
    service = SERVICE,
    target  = TARGET,
    config  = { propagate_baggage = false },
})
report(
    outbound_baggage == nil,
    "propagate_baggage=false leaves baggage untouched",
    nil,
    outbound_baggage
)
report(
    set_target_call ~= nil,
    "propagate_baggage=false still routes",
    "routed",
    set_target_call and "routed"
)

os.exit(failures == 0 and 0 or 1)
