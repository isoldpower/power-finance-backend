local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local response_headers, cleared_headers, logged_warnings = {}, {}, {}

kong = {
    ctx = { shared = {}, plugin = {} },
    log = {
        warn = function(...) logged_warnings[#logged_warnings + 1] = table.concat({ ... }) end,
        err = function() end,
    },
    response = {
        get_header = function(name) return response_headers[name] end,
        set_header = function(name, value) response_headers[name] = value end,
        clear_header = function(name)
            cleared_headers[#cleared_headers + 1] = name
            response_headers[name] = nil
        end,
    },
}

package.loaded["kong.plugins.write-ral-version.utilities"] = {
    retrieve_digest = function() return "digest" end,
    to_hex = function() return "abcd" end,
}
package.loaded["kong.plugins.write-ral-version.redis_writer"] = {}

local handler = dofile(PLUGIN .. "/handler.lua")

local failures = 0
local function check(label, expected, actual)
    local ok = actual == expected
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local function reset(headers, claims)
    response_headers, cleared_headers, logged_warnings = headers, {}, {}
    kong.ctx.shared = { clerk_claims = claims }
    kong.ctx.plugin = {}
end

local function pending_owner()
    local pending_record = kong.ctx.plugin.pending_offset_record
    return pending_record and pending_record.user_id
end

local clerk_route = { hmac_secret = "secret", write_version_header = "X-Write-Version" }
local demo_route = {
    hmac_secret = "secret",
    write_version_header = "X-Write-Version",
    subject_response_header = "X-Demo-Subject",
}

reset({ ["X-Write-Version"] = "42" }, { sub = "user_2abc" })
handler:header_filter(clerk_route)
check("clerk sub owns the offset", "user_2abc", pending_owner())
check("signed version replaces the raw one", "42:abcd", response_headers["X-Write-Version"])
check("no subject header configured clears nothing", 0, #cleared_headers)

reset({ ["X-Write-Version"] = "42", ["X-Demo-Subject"] = "demo_abc" }, nil)
handler:header_filter(clerk_route)
check("upstream subject is ignored when not configured", nil, pending_owner())
check("missing owner is logged", 1, #logged_warnings)

reset({ ["X-Write-Version"] = "57", ["X-Demo-Subject"] = "demo_abc" }, nil)
handler:header_filter(demo_route)
check("upstream subject owns the offset without claims", "demo_abc", pending_owner())
check("upstream subject never leaves the gateway", nil, response_headers["X-Demo-Subject"])

reset({ ["X-Write-Version"] = "57", ["X-Demo-Subject"] = "demo_abc" }, { sub = "user_2abc" })
handler:header_filter(demo_route)
check("clerk sub wins over the upstream subject", "user_2abc", pending_owner())
check("upstream subject is stripped even when unused", nil, response_headers["X-Demo-Subject"])

reset({ ["X-Demo-Subject"] = "demo_abc" }, nil)
handler:header_filter(demo_route)
check("subject is stripped when no version is returned", nil, response_headers["X-Demo-Subject"])
check("no version records nothing", nil, pending_owner())

reset({ ["X-Write-Version"] = "57", ["X-Demo-Subject"] = "" }, nil)
handler:header_filter(demo_route)
check("empty upstream subject records nothing", nil, pending_owner())

os.exit(failures == 0 and 0 or 1)
