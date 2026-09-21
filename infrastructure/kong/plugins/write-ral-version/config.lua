local REDIS_CONFIG = {
    DEFAULT_KEY_PREFIX  = "ral:user:",
    DEFAULT_TTL_SECONDS = 604800,
    KEEPALIVE_TIMEOUT_MS = 60000,
    KEEPALIVE_POOL_SIZE  = 100,
}

local exports = {
    RedisConnection = REDIS_CONFIG,
}

return exports