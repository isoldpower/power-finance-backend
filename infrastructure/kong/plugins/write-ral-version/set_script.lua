-- Monotonic SET — refuses to lower a stored offset, so concurrent /
-- retried writes from the same user can't roll the value backwards.
local MONOTONIC_SET_SCRIPT = [[
    local existing = redis.call('GET', KEYS[1])
    if not existing or tonumber(ARGV[1]) > tonumber(existing) then
        redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
        return 1
    end
    return 0
]]


local exports = {
    MONOTONIC_SET_SCRIPT = MONOTONIC_SET_SCRIPT,
}

return exports