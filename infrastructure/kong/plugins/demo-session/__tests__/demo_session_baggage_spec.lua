local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local inbound_headers, inbound_query, outbound_headers = {}, {}, {}
kong = {
    request = {
        get_header = function(name) return inbound_headers[name] end,
        get_query_arg = function(name) return inbound_query[name] end,
    },
    service = {
        request = {
            set_header = function(name, value) outbound_headers[name] = value end,
        },
    },
}

package.loaded["kong.plugins.demo-session.config"] = dofile(PLUGIN .. "/config.lua")

local demo_session_baggage = dofile(PLUGIN .. "/demo_session_baggage.lua")

local failures = 0
local function check(label, expected, actual)
    local ok = actual == expected
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local function given(headers, query)
    inbound_headers, inbound_query, outbound_headers = headers or {}, query or {}, {}
end

local valid_identifier = "f3b1c2d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d"

given({})
check("nothing is presented without header or query", 0,
    #demo_session_baggage.read_presented_identifiers("X-Demo-Session", "demo_session"))

given({ ["X-Demo-Session"] = "" })
check("an empty header counts as absent", 0,
    #demo_session_baggage.read_presented_identifiers("X-Demo-Session", nil))

given({ ["X-Demo-Session"] = valid_identifier }, { demo_session = "from-query" })
local presented = demo_session_baggage.read_presented_identifiers("X-Demo-Session", "demo_session")
check("header and query are both presented", 2, #presented)
check("the header comes first", valid_identifier, presented[1])
check("the query comes second", "from-query", presented[2])

given({}, { session = "from-query" })
check("the query is ignored without a configured parameter", 0,
    #demo_session_baggage.read_presented_identifiers("X-Demo-Session", nil))

given({}, { demo_session = true })
check("a valueless query argument is still presented", true,
    demo_session_baggage.read_presented_identifiers("X-Demo-Session", "demo_session")[1])

check("entry is appended to empty baggage", "demo-session=" .. valid_identifier,
    demo_session_baggage.replace_baggage_entry(nil, "demo-session", valid_identifier))

check("entry is appended after existing entries",
    "sandbox-id=nikita,demo-session=" .. valid_identifier,
    demo_session_baggage.replace_baggage_entry("sandbox-id=nikita", "demo-session", valid_identifier))

check("client supplied entry is replaced",
    "sandbox-id=nikita,demo-session=" .. valid_identifier,
    demo_session_baggage.replace_baggage_entry(
        "demo-session=forged, sandbox-id=nikita", "demo-session", valid_identifier))

given({ baggage = "sandbox-id=nikita" })
demo_session_baggage.propagate_demo_session(valid_identifier)
check("propagation writes the upstream baggage header",
    "sandbox-id=nikita,demo-session=" .. valid_identifier, outbound_headers.baggage)

os.exit(failures == 0 and 0 or 1)
