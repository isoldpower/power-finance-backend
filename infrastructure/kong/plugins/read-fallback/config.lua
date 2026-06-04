local KEEPALIVE_TIMEOUT_MS = 60000
local KEEPALIVE_POOL_SIZE  = 100

local SKIP_HEADERS = {
    ["connection"]          = true,
    ["keep-alive"]          = true,
    ["proxy-authenticate"]  = true,
    ["proxy-authorization"] = true,
    ["te"]                  = true,
    ["trailers"]            = true,
    ["transfer-encoding"]   = true,
    ["upgrade"]             = true,
    ["content-length"]      = true,
    ["host"]                = true,
}

return {
    KEEPALIVE_POOL_SIZE = KEEPALIVE_POOL_SIZE,
    KEEPALIVE_TIMEOUT_MS = KEEPALIVE_TIMEOUT_MS,
    SKIP_HEADERS = SKIP_HEADERS,
}