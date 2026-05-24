local http         = require "resty.http"
local cjson        = require "cjson.safe"
local resty_lock   = require "resty.lock"
local shared_cache = require "kong.plugins.clerk-jwt.redis_cache"
local utilities    = require "kong.plugins.clerk-jwt.utilities"


local JWKS_KNOWN_PATH = "/.well-known/jwks.json"
local LOCKS_DICT_NAME = "clerk_jwks_locks"
local JWKS_LOCK_KEY   = "jwks"


--- Remove any trailing forward slashes from a URL.
-- Issuer URLs are supplied by operators and may or may not end with
-- a slash; we strip them so concatenation with the well-known path
-- never produces a double slash (`//.well-known/...`).
--
-- @param url string  any URL or URL prefix
-- @return string  the input with all trailing slashes removed
local strip_trailing_slash = function(url)
    return (url:gsub("/+$", ""))
end


--- Perform the actual JWKS HTTP GET and decode the body.
-- Returns nil + a human-readable error on any failure mode: transport
-- error, non-200 status, or malformed JSON body. The caller is
-- responsible for further structural validation (presence of `keys`).
--
-- @param http_connection table  resty.http client instance
-- @param issuer_url string  issuer base URL (slashes will be stripped)
-- @return table|nil  decoded JWKS body on success
-- @return string|nil  error message on failure
local safe_make_request = function(http_connection, issuer_url)
    local request_url = strip_trailing_slash(issuer_url) .. JWKS_KNOWN_PATH
    local response, request_error = http_connection:request_uri(request_url, {
        method = "GET",
        ssl_verify = true,
    })

    if not response then
        return nil, "JWKS fetch failed: " .. (request_error or "Unknown Error")
    elseif response.status ~= 200 then
        return nil, "JWKS fetch non-200: " .. tostring(response.status)
    end

    local decoded, decode_error = cjson.decode(response.body)
    if not decoded then
        return nil, "JWKS body decode failed: " .. (decode_error or "Unknown Error")
    end

    return decoded, nil
end


--- Fetch and structurally validate a JWKS document from the issuer.
-- Validates that the response is a table containing a `keys` array;
-- anything else is treated as a malformed payload.
--
-- @param issuer_url string  issuer base URL
-- @param timeout_ms number|nil  HTTP timeout in milliseconds (default 5000)
-- @return table|nil  validated JWKS document
-- @return string|nil  error message on failure
local fetch_jwks = function(issuer_url, timeout_ms)
    local http_connection = http.new()
    http_connection:set_timeout(timeout_ms or 5000)

    local parsed_message, request_error = safe_make_request(http_connection, issuer_url)
    if request_error then
        return nil, request_error
    elseif type(parsed_message) ~= "table" or type(parsed_message.keys) ~= "table" then
        return nil, "JWKS payload malformed and is not a table"
    end

    return parsed_message
end


--- Fetch JWKS from the issuer and write the result into the shared
-- cache. Used as the inner step of `fetch_and_cache_jwks`, and as
-- the fallback path when the lock dict is missing.
--
-- @param config table  plugin config (issuer_url, http_timeout_ms, jwks_ttl_seconds)
-- @return table|nil  the freshly fetched JWKS
-- @return string|nil  error message on failure
local direct_fetch_and_cache = function(config)
    local fresh_jwks, fetch_error = fetch_jwks(config.issuer_url, config.http_timeout_ms)
    if not fresh_jwks then
        return nil, fetch_error
    end

    shared_cache.set_cache_value(config, fresh_jwks)
    return fresh_jwks, nil
end


--- Single-flight JWKS fetch via lua-resty-lock.
--
-- Only one worker at a time fetches JWKS for a given key; queued
-- workers re-read the cache after the holder finishes so they reuse
-- the fresh value instead of hammering Clerk.
--
-- Requires shared dict `clerk_jwks_locks` declared in nginx.conf.
-- If the dict is missing we still serve the request (degraded) but
-- log loudly — under load this allows a thundering herd against
-- Clerk's JWKS endpoint.
--
-- @param config table  plugin config
-- @return table|nil  the JWKS document
-- @return string|nil  error message on failure
local fetch_and_cache_jwks = function(config)
    local lock_timeout_seconds = (config.http_timeout_ms or 5000) / 1000
    local lock, lock_init_error = resty_lock:new(LOCKS_DICT_NAME, {
        timeout = lock_timeout_seconds,
        exptime = lock_timeout_seconds * 2,
    })
    if not lock then
        kong.log.err("clerk-jwt: lock dict '", LOCKS_DICT_NAME,
            "' unavailable, falling back to unlocked fetch (stampede risk): ",
            lock_init_error or "Unknown Error")
        return direct_fetch_and_cache(config)
    end

    local elapsed, lock_error = lock:lock(JWKS_LOCK_KEY)
    if not elapsed then
        return nil, "JWKS lock acquire failed: " .. (lock_error or "Unknown Error")
    end

    local cached = shared_cache.get_cache_value(config)
    if cached then
        lock:unlock()
        return cached, nil
    end

    local fresh_jwks, fetch_error = direct_fetch_and_cache(config)
    lock:unlock()
    return fresh_jwks, fetch_error
end


--- Return the JWKS document, preferring the shared cache.
--
-- The third return value tells the caller whether the value came
-- from cache — important because a kid miss on a *cached* response
-- may indicate key rotation and should trigger a refetch, while a
-- miss on a freshly fetched response is genuinely unknown.
--
-- @param config table  plugin config
-- @return table|nil  the JWKS document
-- @return boolean  true if served from cache, false if just fetched
-- @return string|nil  error message on failure
local get_jwks_with_cache = function(config)
    local cached_value = shared_cache.get_cache_value(config)
    if cached_value then
        return cached_value, true, nil
    end

    local fresh_jwks, fetch_error = fetch_and_cache_jwks(config)
    if not fresh_jwks then
        return nil, false, fetch_error
    end

    return fresh_jwks, false, nil
end


--- Resolve the JWK that matches a given kid, refetching on miss.
--
-- Clerk rotates signing keys; a cached JWKS may miss the kid on a
-- freshly issued token. On miss against a cached response we
-- invalidate and refetch once, then look up the kid again. On miss
-- against an already-fresh response we give up — refetching would
-- not help.
--
-- @param config table  plugin config
-- @param kid string  the `kid` header value from the unverified JWT
-- @return table|nil  the matching JWK dict
-- @return string|nil  error message on JWKS retrieval failure (nil for plain key miss)
local resolve_jwk_for_kid = function(config, kid)
    local jwks_pair, was_cached, fetch_error = get_jwks_with_cache(config)
    if not jwks_pair then
        return nil, fetch_error
    end

    local matched = utilities.find_key_for_kid(jwks_pair, kid)
    if matched then
        return matched, nil
    end
    if not was_cached then
        return nil, nil
    end

    shared_cache.invalidate_cache(config)
    local fresh_jwks, refetch_error = fetch_and_cache_jwks(config)
    if not fresh_jwks then
        return nil, refetch_error
    end

    return utilities.find_key_for_kid(fresh_jwks, kid), nil
end


local exports = {
    fetch_jwks          = fetch_jwks,
    resolve_jwk_for_kid = resolve_jwk_for_kid,
}

return exports
