-- Which verification path a token takes. A Clerk session token must be RS256,
-- or an attacker could sign HS256 with Clerk's public key; a guest demo token is
-- HS256 with the demo issuer and is verified against the shared secret instead.
local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

package.loaded["resty.jwt"] = {
    load_jwt = function() return nil end,
    verify_jwt_obj = function() error("the pinned algorithm must reject before verification") end,
}
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

local DEMO_ISSUER = "power-finance-demo"
local function token(alg, issuer)
    return { header = { alg = alg, typ = "JWT" }, payload = { iss = issuer, sub = "demo_abc" } }
end

check("an HS256 token from the demo issuer is a demo token", true,
    utilities.is_demo_token(token("HS256", DEMO_ISSUER), DEMO_ISSUER))
check("an RS256 token is never a demo token", false,
    utilities.is_demo_token(token("RS256", DEMO_ISSUER), DEMO_ISSUER))
check("an HS256 token from another issuer is not a demo token", false,
    utilities.is_demo_token(token("HS256", "https://clerk.powerfinance.site"), DEMO_ISSUER))
check("nothing is a demo token when no demo issuer is configured", false,
    utilities.is_demo_token(token("HS256", DEMO_ISSUER), nil))
check("a token without a payload is not a demo token", false,
    utilities.is_demo_token({ header = { alg = "HS256" } }, DEMO_ISSUER))

check("the Clerk path refuses an HS256 token before verifying it", nil,
    utilities.get_verified_jwt("-----BEGIN PUBLIC KEY-----", token("HS256", "https://clerk.example"), {}))
check("the Clerk path refuses an unsigned token", nil,
    utilities.get_verified_jwt("-----BEGIN PUBLIC KEY-----", token("none", "https://clerk.example"), {}))
check("the demo path refuses an RS256 token before verifying it", nil,
    utilities.get_verified_demo_jwt("secret", token("RS256", DEMO_ISSUER), { issuer = DEMO_ISSUER }))

check("RS256 is recognised", true, utilities.has_signing_algorithm(token("RS256"), "RS256"))
check("a missing header is not any algorithm", false, utilities.has_signing_algorithm({}, "RS256"))

if failures > 0 then
    print(failures .. " check(s) failed")
    os.exit(1)
end
print("all checks passed")
