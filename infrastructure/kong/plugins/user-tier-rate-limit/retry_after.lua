--- How long a throttled caller should wait before trying again.


--- How long until this window would admit one more request, assuming the
-- caller stops sending in the meantime.
--
-- @param evaluated_window table  one row of the counter's reply
-- @return number  whole seconds to wait, at least 1
local seconds_until_admitted = function(evaluated_window)
    local headroom = evaluated_window.limit - evaluated_window.current
    local previous = evaluated_window.previous

    if headroom > 0 and previous > 0 then
        local decayed_at = evaluated_window.seconds
            - (headroom * evaluated_window.seconds / previous)

        return math.max(1, math.ceil(decayed_at - evaluated_window.elapsed))
    end

    return math.max(1, math.ceil(evaluated_window.seconds - evaluated_window.elapsed))
end


--- Longest wait across the windows that rejected the request.
-- Backing off for the shorter one would only trip the longer one again.
--
-- @param evaluated table  the counter's reply
-- @return number  whole seconds to wait, at least 1
local retry_after_seconds = function(evaluated)
    local retry_after = 1

    for _, evaluated_window in ipairs(evaluated.windows) do
        if evaluated_window.estimate > evaluated_window.limit then
            retry_after = math.max(retry_after, seconds_until_admitted(evaluated_window))
        end
    end

    return retry_after
end


local exports = {
    seconds_until_admitted = seconds_until_admitted,
    retry_after_seconds    = retry_after_seconds,
}

return exports
