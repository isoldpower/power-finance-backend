local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local scheduled_timers, recorded_offsets, logged_warnings = {}, {}, {}
local timer_scheduling_error = nil

ngx = {
    timer = {
        at = function(delay, callback, ...)
            if timer_scheduling_error then
                return nil, timer_scheduling_error
            end
            scheduled_timers[#scheduled_timers + 1] = { delay = delay, callback = callback, arguments = { ... } }
            return true
        end,
    },
}

kong = {
    ctx = { plugin = {} },
    log = { warn = function(...) logged_warnings[#logged_warnings + 1] = table.concat({ ... }) end },
}

package.loaded["kong.plugins.write-ral-version.utilities"] = {}
package.loaded["kong.plugins.write-ral-version.redis_writer"] = {
    set_user_offset_monotonic = function(config, user_id, raw_version)
        recorded_offsets[#recorded_offsets + 1] = user_id .. "=" .. raw_version
        return true
    end,
}

local handler = dofile(PLUGIN .. "/handler.lua")

local failures = 0
local function check(label, expected, actual)
    local ok = actual == expected
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local plugin_config = { redis_host = "gateway-redis" }

handler:log(plugin_config)
check("no pending record schedules nothing", 0, #scheduled_timers)

kong.ctx.plugin.pending_offset_record = { user_id = "user_2abc", raw_version = "42" }
handler:log(plugin_config)
check("log phase only schedules the redis write", 0, #recorded_offsets)
check("one timer is scheduled", 1, #scheduled_timers)
check("timer runs immediately", 0, scheduled_timers[1].delay)

scheduled_timers[1].callback(false, unpack(scheduled_timers[1].arguments))
check("timer records the offset", "user_2abc=42", recorded_offsets[1])

scheduled_timers[1].callback(true, unpack(scheduled_timers[1].arguments))
check("premature timer on shutdown records nothing", 1, #recorded_offsets)

timer_scheduling_error = "too many pending timers"
handler:log(plugin_config)
check("scheduling failure is logged, not raised", 1, #logged_warnings)

os.exit(failures == 0 and 0 or 1)
