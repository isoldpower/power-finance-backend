-- Precedence of the three channels a sandbox id can arrive on. The query argument
-- exists because a browser cannot set headers on a WebSocket handshake, and it is
-- tried last: baggage is a decision already taken upstream, and a header is set by a
-- client that could equally have written the URL.
local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local headers, query = {}, {}
kong = {
    request = {
        get_header    = function(name) return headers[name] end,
        get_query_arg = function(name) return query[name] end,
    },
    service = { request = { set_header = function() end } },
    router  = { get_service = function() return nil end },
    log     = { warn = function() end, err = function() end, debug = function() end },
    ctx     = { shared = {} },
}

package.loaded["kong.plugins.sandbox-router.config"] = dofile(PLUGIN .. "/config.lua")
package.loaded["kong.plugins.sandbox-router.baggage_parser"] =
    dofile(PLUGIN .. "/baggage_parser.lua")

local sandbox_resolver = dofile(PLUGIN .. "/sandbox_resolver.lua")

local failures = 0
local function check(label, expected)
    local actual = sandbox_resolver.resolve_sandbox().sandbox_id
    local ok = actual == expected
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local function check_from_baggage(label, expected)
    local actual = sandbox_resolver.resolve_sandbox().from_baggage
    local ok = actual == expected
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local function given(h, q) headers, query = h or {}, q or {} end

given({}, {})
check("nothing set resolves to nil", nil)

given({}, { sandbox = "nikita" })
check("query argument alone is used", "nikita")

given({ ["X-Sandbox"] = "from-header" }, { sandbox = "from-query" })
check("header beats query", "from-header")

given({ baggage = "sandbox-id=from-baggage" }, { sandbox = "from-query" })
check("baggage beats query", "from-baggage")

given({ baggage = "sandbox-id=from-baggage", ["X-Sandbox"] = "from-header" }, { sandbox = "from-query" })
check("baggage beats both", "from-baggage")

given({}, { sandbox = "" })
check("empty query argument is ignored", nil)

given({}, { sandbox = { "first", "second" } })
check("repeated argument takes the first", "first")

given({ ["X-Sandbox"] = "" }, { sandbox = "from-query" })
check("empty header falls through to query", "from-query")

given({ baggage = "team=core,sandbox-id=tagged,tier=free" }, {})
check("baggage entry is found among others", "tagged")

given({ baggage = "sandbox-id=tagged" }, {})
check_from_baggage("an id already in baggage is not re-propagated", true)

given({ ["X-Sandbox"] = "from-header" }, {})
check_from_baggage("an id from the header is propagated", false)

given({}, { sandbox = "from-query" })
check_from_baggage("an id from the query argument is propagated", false)

os.exit(failures == 0 and 0 or 1)
