-- How a token is taken off a request. Both paths matter: ordinary requests use
-- Authorization, and a browser cannot set headers on a WebSocket handshake, so
-- the token rides the subprotocol list there instead.
local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

-- resty.jwt ships only in the custom gateway image, and resty.openssl.pkey
-- resolves OpenSSL symbols that exist under nginx but not under bare luajit.
-- Only the pure helpers are exercised here, so stub what the module loads.
package.loaded["resty.jwt"] = { load_jwt = function() return nil end }
package.loaded["resty.openssl.pkey"] = { new = function() return nil, "stubbed" end }
package.loaded["cjson.safe"] = { encode = function() return nil end, decode = function() return nil end }
kong = { log = { err = function() end, warn = function() end, debug = function() end } }

local utilities = dofile(PLUGIN .. "/utilities.lua")

local failures = 0
local function check(label, expected, actual)
    local ok = expected == actual
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

check("a bearer token is extracted", "abc.def.ghi",
    utilities.extract_bearer("Bearer abc.def.ghi"))
check("the scheme is case-insensitive", "abc.def.ghi",
    utilities.extract_bearer("bearer abc.def.ghi"))
check("an upper-case scheme is accepted", "abc.def.ghi",
    utilities.extract_bearer("BEARER abc.def.ghi"))
check("extra whitespace is tolerated", "abc.def.ghi",
    utilities.extract_bearer("Bearer    abc.def.ghi"))
check("a nil header yields nil", nil, utilities.extract_bearer(nil))
check("an empty header yields nil", nil, utilities.extract_bearer(""))
check("a non-bearer scheme is refused", nil, utilities.extract_bearer("Basic abc"))
check("a bare token without a scheme is refused", nil, utilities.extract_bearer("abc.def.ghi"))
check("a scheme with no token is refused", nil, utilities.extract_bearer("Bearer"))
check("a scheme with only spaces is refused", nil, utilities.extract_bearer("Bearer   "))

local MARKER = "clerk"
check("a two-entry subprotocol pair yields the token", "tok",
    utilities.extract_subprotocol_token("clerk, tok", MARKER))
check("surrounding whitespace is trimmed", "tok",
    utilities.extract_subprotocol_token("  clerk ,  tok  ", MARKER))
check("a nil header yields nil", nil,
    utilities.extract_subprotocol_token(nil, MARKER))
check("an empty header yields nil", nil,
    utilities.extract_subprotocol_token("", MARKER))
check("a single entry is refused", nil,
    utilities.extract_subprotocol_token("clerk", MARKER))
check("three entries are refused", nil,
    utilities.extract_subprotocol_token("clerk, tok, extra", MARKER))
check("a wrong marker is refused", nil,
    utilities.extract_subprotocol_token("other, tok", MARKER))
check("the marker must come first", nil,
    utilities.extract_subprotocol_token("tok, clerk", MARKER))

local JWKS = { keys = { { kid = "key-1", kty = "RSA" }, { kid = "key-2", kty = "RSA" } } }
local found = utilities.find_key_for_kid(JWKS, "key-2")
check("a key is found by kid", "key-2", found and found.kid)
check("an unknown kid yields nil", nil, utilities.find_key_for_kid(JWKS, "key-3"))
check("a nil kid yields nil", nil, utilities.find_key_for_kid(JWKS, nil))

check("no configured parties accepts any azp", true,
    utilities.check_authorized_party({ payload = { azp = "anything" } }, nil))
check("an empty party list accepts any azp", true,
    utilities.check_authorized_party({ payload = { azp = "anything" } }, {}))
check("a listed azp is accepted", true,
    utilities.check_authorized_party({ payload = { azp = "https://app.example" } },
        { "https://app.example" }))
check("an unlisted azp is refused", false,
    utilities.check_authorized_party({ payload = { azp = "https://evil.example" } },
        { "https://app.example" }))

os.exit(failures == 0 and 0 or 1)
