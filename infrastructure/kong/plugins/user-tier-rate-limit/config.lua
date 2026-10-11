local WINDOWS = {
    {
        label = "minute",
        seconds = 60,
        header_suffix = "Minute",
        config_key = "per_minute",
    },
    {
        label = "hour",
        seconds = 3600,
        header_suffix = "Hour",
        config_key = "per_hour",
    },
}

local DEMO_WINDOWS = {
    {
        label = "minute",
        seconds = 60,
        header_suffix = "Minute",
        config_key = "demo_per_minute",
    },
    {
        label = "hour",
        seconds = 3600,
        header_suffix = "Hour",
        config_key = "demo_per_hour",
    },
}

local REDIS_CONFIG = {
    KEEPALIVE_TIMEOUT_MS = 60000,
    KEEPALIVE_POOL_SIZE  = 100,
    TTL_WINDOWS = 2,
}


local exports = {
    LimitingWindows = WINDOWS,
    DemoLimitingWindows = DEMO_WINDOWS,
    RedisConnection = REDIS_CONFIG,
}

return exports