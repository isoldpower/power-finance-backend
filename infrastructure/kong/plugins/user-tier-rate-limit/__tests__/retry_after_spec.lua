-- Retry-After on a 429. Too low and a well-behaved client hammers a limit it
-- cannot clear; too high and it waits longer than it needs to. The value is a
-- sliding-window estimate, so it is worth pinning.
local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local retry_after = dofile(PLUGIN .. "/retry_after.lua")

local failures = 0
local function check(label, expected, actual)
    local ok = expected == actual
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local function window(overrides)
    local evaluated_window = {
        seconds = 60,
        limit = 10,
        current = 10,
        previous = 0,
        estimate = 11,
        elapsed = 30,
    }
    for key, value in pairs(overrides or {}) do
        evaluated_window[key] = value
    end

    return evaluated_window
end

check("with no previous window, wait out the remainder", 30,
    retry_after.seconds_until_admitted(window()))
check("late in the window, the wait shrinks", 5,
    retry_after.seconds_until_admitted(window({ elapsed = 55 })))
check("at the very end, the wait floors at 1", 1,
    retry_after.seconds_until_admitted(window({ elapsed = 60 })))
check("past the end, the wait still floors at 1", 1,
    retry_after.seconds_until_admitted(window({ elapsed = 75 })))

-- With headroom against a populated previous window the limit clears by decay
-- rather than by the window rolling over, so the wait is shorter.
check("decay against a previous window admits sooner", 20,
    retry_after.seconds_until_admitted(
        window({ current = 8, previous = 6, estimate = 11, elapsed = 20 })
    ))
check("no headroom falls back to the window remainder", 40,
    retry_after.seconds_until_admitted(
        window({ current = 10, previous = 6, estimate = 11, elapsed = 20 })
    ))

check("an allowed window contributes nothing", 1,
    retry_after.retry_after_seconds({ windows = { window({ estimate = 3 }) } }))
check("a single tripped window sets the wait", 30,
    retry_after.retry_after_seconds({ windows = { window() } }))
check("the longest tripped window wins", 600,
    retry_after.retry_after_seconds({
        windows = {
            window(),
            window({ seconds = 3600, elapsed = 3000, limit = 100, current = 100, estimate = 101 }),
        },
    }))
check("an untripped long window does not extend the wait", 30,
    retry_after.retry_after_seconds({
        windows = {
            window(),
            window({ seconds = 3600, elapsed = 3000, limit = 100, current = 40, estimate = 41 }),
        },
    }))
check("no windows at all yields the floor", 1,
    retry_after.retry_after_seconds({ windows = {} }))

os.exit(failures == 0 and 0 or 1)
