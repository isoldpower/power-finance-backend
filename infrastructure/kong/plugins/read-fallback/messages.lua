-- Error responses for the read-fallback plugin, in the API's standard
-- error envelope.

local envelope = require "power_finance.envelope"


--- 503 when the gateway itself cannot reach an upstream while proxying.
-- `which` names the leg that failed ("Read Service" / "Write Service
-- fallback") so logs and clients can tell them apart.
local upstream_unreachable = function(which)
    return envelope.exit(
        503,
        "service_unavailable",
        "Gateway could not reach the " .. which .. "."
    )
end


return {
    upstream_unreachable = upstream_unreachable,
}
