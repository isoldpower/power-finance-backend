-- read-fallback rewrites a read path onto its write-side twin when the read
-- model is stale. A wrong rewrite serves the client a 404 from the fallback,
-- which looks like missing data rather than a routing mistake.
local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local utilities = dofile(PLUGIN .. "/utilities.lua")

local failures = 0
local function check(label, expected, actual)
    local ok = expected == actual
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local READ_PREFIX = "/api/v1"
local FALLBACK_PREFIX = "/api/v1/fallback-reads"

check("a matching prefix is swapped", "/api/v1/fallback-reads/wallets",
    utilities.build_fallback_path("/api/v1/wallets", READ_PREFIX, FALLBACK_PREFIX))
check("a nested path keeps its tail", "/api/v1/fallback-reads/wallets/abc-123",
    utilities.build_fallback_path("/api/v1/wallets/abc-123", READ_PREFIX, FALLBACK_PREFIX))
check("an exact-prefix path maps to the bare fallback", "/api/v1/fallback-reads",
    utilities.build_fallback_path("/api/v1", READ_PREFIX, FALLBACK_PREFIX))
check("a non-matching prefix yields nil", nil,
    utilities.build_fallback_path("/health/live", READ_PREFIX, FALLBACK_PREFIX))
check("a partially-matching prefix yields nil", nil,
    utilities.build_fallback_path("/api/v2/wallets", READ_PREFIX, FALLBACK_PREFIX))

local function response_with(content_type)
    return { headers = { ["Content-Type"] = content_type } }
end

check("a json response is an api response", true,
    utilities.is_api_response(response_with("application/json")))
check("a charset suffix is tolerated", true,
    utilities.is_api_response(response_with("application/json; charset=utf-8")))
check("casing is ignored", true,
    utilities.is_api_response(response_with("Application/JSON")))
check("a repeated header takes the first value", true,
    utilities.is_api_response({ headers = { ["Content-Type"] = { "application/json" } } }))
check("an html response is not an api response", false,
    utilities.is_api_response(response_with("text/html")))
check("a missing content type is not an api response", false,
    utilities.is_api_response({ headers = {} }))
check("a response with no headers is not an api response", false,
    utilities.is_api_response({}))
check("json mentioned later in the value does not count", false,
    utilities.is_api_response(response_with("text/html; x=application/json")))

os.exit(failures == 0 and 0 or 1)
