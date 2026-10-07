local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local inbound_headers, outbound_headers = {}, {}
kong = {
    request = {
        get_header = function(name) return inbound_headers[name] end,
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

local function given(headers)
    inbound_headers, outbound_headers = headers or {}, {}
end

local valid_identifier = "f3b1c2d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d"

check("uuid identifier is valid", true,
    demo_session_baggage.is_valid_demo_session_identifier(valid_identifier))
check("short identifier is rejected", false,
    demo_session_baggage.is_valid_demo_session_identifier("short"))
check("overlong identifier is rejected", false,
    demo_session_baggage.is_valid_demo_session_identifier(string.rep("a", 65)))
check("identifier with baggage delimiters is rejected", false,
    demo_session_baggage.is_valid_demo_session_identifier("abcdefghijklmnop,sandbox-id=x"))
check("missing identifier is rejected", false,
    demo_session_baggage.is_valid_demo_session_identifier(nil))

given({ ["X-Demo-Session"] = valid_identifier })
check("header identifier is read", valid_identifier,
    demo_session_baggage.read_demo_session_identifier("X-Demo-Session"))

given({ ["X-Demo-Session"] = "bad value with spaces" })
check("invalid header identifier is ignored", nil,
    demo_session_baggage.read_demo_session_identifier("X-Demo-Session"))

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
