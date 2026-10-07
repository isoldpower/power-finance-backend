local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

package.loaded["kong.plugins.demo-session.config"] = dofile(PLUGIN .. "/config.lua")
package.loaded["power_finance.gateway_trace_context"] = {}

local demo_session_tracing = dofile(PLUGIN .. "/demo_session_tracing.lua")

local failures = 0
local function check(label, expected, actual)
    local ok = actual == expected
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local function new_span(name)
    return {
        name = name,
        attributes = {},
        set_attribute = function(self, key, value) self.attributes[key] = value end,
    }
end

local request_spans = { new_span("kong"), new_span("kong.balancer"), new_span("kong.access.plugin.cors") }
demo_session_tracing.tag_request_spans(request_spans, "portfolio-visitor-session")

for _, request_span in ipairs(request_spans) do
    check(request_span.name .. " carries the demo session", "portfolio-visitor-session",
        request_span.attributes["demo-session"])
end

local tagged_without_spans = pcall(demo_session_tracing.tag_request_spans, nil, "portfolio-visitor-session")
check("missing span list is tolerated", true, tagged_without_spans)

os.exit(failures == 0 and 0 or 1)
