-- The sliding-window redis script

local REDIS_SCRIPT = [==[
-- KEYS  per window: current bucket key, previous bucket key
-- ARGV  [1] window count, then per window: limit, previous weight, key ttl
-- reply [1] 1 when admitted, then per window: previous, current, estimate

local window_count = tonumber(ARGV[1])
local allowed = 1
local readings = {}

for index = 1, window_count do
    local argument_base = 1 + (index - 1) * 3
    local limit = tonumber(ARGV[argument_base + 1])
    local previous_weight = tonumber(ARGV[argument_base + 2])

    local previous = tonumber(redis.call('GET', KEYS[index * 2]) or '0')
    local current = tonumber(redis.call('GET', KEYS[index * 2 - 1]) or '0')
    local estimated = previous * previous_weight + current + 1

    readings[index] = { previous, current, estimated }
    if estimated > limit then
        allowed = 0
    end
end

local reply = { allowed }

for index = 1, window_count do
    local reading = readings[index]

    if allowed == 1 then
        local argument_base = 1 + (index - 1) * 3
        redis.call('INCR', KEYS[index * 2 - 1])
        redis.call('EXPIRE', KEYS[index * 2 - 1], tonumber(ARGV[argument_base + 3]))
    end

    reply[#reply + 1] = reading[1]
    reply[#reply + 1] = reading[2]
    reply[#reply + 1] = math.ceil(reading[3])
end

return reply
]==]

return {
    REDIS_SCRIPT = REDIS_SCRIPT,
}
