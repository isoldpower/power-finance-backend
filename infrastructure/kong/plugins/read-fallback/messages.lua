--- 502 when the gateway itself cannot reach an upstream while proxying.
-- `which` names the leg that failed ("Read Service" / "Write Service
-- fallback") so logs and clients can tell them apart.
local upstream_unreachable = function(which)
    return kong.response.exit(502, {
        message = "Gateway could not reach the " .. which .. ".",
    })
end


return {
    upstream_unreachable = upstream_unreachable,
}
