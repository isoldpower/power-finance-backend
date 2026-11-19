local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

package.loaded["kong.plugins.demo-session.config"] = dofile(PLUGIN .. "/config.lua")

local demo_visit_identifier = dofile(PLUGIN .. "/demo_visit_identifier.lua")

local failures = 0
local function check(label, expected, actual)
    local ok = actual == expected
    if not ok then failures = failures + 1 end
    print((ok and "ok   " or "FAIL ") .. label
        .. "  expected=" .. tostring(expected) .. " actual=" .. tostring(actual))
end

local SECRET = "a-demo-session-secret-of-at-least-32-characters"
local WRITE_SERVICE_IDENTIFIER = "dv1_q8n3V0kz5tX2bYp1mW7cRg_1vuhmo0_5kLPnLI9aV1kvR4cILOTig"
local WRITE_SERVICE_NONCE = "q8n3V0kz5tX2bYp1mW7cRg"
local WRITE_SERVICE_EXPIRY = 4102444800
local BEFORE_EXPIRY = WRITE_SERVICE_EXPIRY - 1

local function verifies(secret, identifier, now)
    local verified_visit = demo_visit_identifier.verify(secret, identifier, now or BEFORE_EXPIRY)
    return verified_visit ~= nil
end

local function replace_character(text, position, replacement)
    return text:sub(1, position - 1) .. replacement .. text:sub(position + 1)
end

check("base64url of 16 zero bytes", "AAAAAAAAAAAAAAAAAAAAAA",
    demo_visit_identifier.encode_base64url(string.rep("\0", 16)))
check("base64url uses the url-safe alphabet", "-_8",
    demo_visit_identifier.encode_base64url("\251\255"))

local verified_visit = demo_visit_identifier.verify(SECRET, WRITE_SERVICE_IDENTIFIER, BEFORE_EXPIRY)
check("an identifier issued by write-service verifies", true, verified_visit ~= nil)
check("the verified nonce is the visit identity", WRITE_SERVICE_NONCE, verified_visit and verified_visit.nonce)
check("the verified expiry is decoded from base36", WRITE_SERVICE_EXPIRY,
    verified_visit and verified_visit.expires_at)

check("the identifier fits the legacy demo session shape", true,
    #WRITE_SERVICE_IDENTIFIER <= 64 and WRITE_SERVICE_IDENTIFIER:match("^[%w_%-]+$") ~= nil)

check("an expired identifier is rejected", false,
    verifies(SECRET, WRITE_SERVICE_IDENTIFIER, WRITE_SERVICE_EXPIRY))
check("another secret rejects the identifier", false,
    verifies(SECRET .. "x", WRITE_SERVICE_IDENTIFIER))
check("an empty secret rejects everything", false, verifies("", WRITE_SERVICE_IDENTIFIER))
check("a missing secret rejects everything", false, verifies(nil, WRITE_SERVICE_IDENTIFIER))

check("a tampered nonce is rejected", false,
    verifies(SECRET, replace_character(WRITE_SERVICE_IDENTIFIER, 5, "Z")))
check("an extended expiry is rejected", false,
    verifies(SECRET, (WRITE_SERVICE_IDENTIFIER:gsub("_1vuhmo0_", "_2vuhmo0_"))))
check("a tampered mac is rejected", false,
    verifies(SECRET, replace_character(WRITE_SERVICE_IDENTIFIER, #WRITE_SERVICE_IDENTIFIER, "A")))
check("another version prefix is rejected", false,
    verifies(SECRET, "dv2" .. WRITE_SERVICE_IDENTIFIER:sub(4)))

check("a legacy uuid identifier is rejected", false,
    verifies(SECRET, "f3b1c2d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d"))
check("an uppercase expiry is rejected", false,
    verifies(SECRET, (WRITE_SERVICE_IDENTIFIER:gsub("_1vuhmo0_", "_1VUHMO0_"))))
check("a missing separator is rejected", false,
    verifies(SECRET, replace_character(WRITE_SERVICE_IDENTIFIER, 27, "a")))
check("an overlong identifier is rejected", false,
    verifies(SECRET, WRITE_SERVICE_IDENTIFIER .. string.rep("a", 10)))
check("a non-string identifier is rejected", false, verifies(SECRET, true))
check("baggage delimiters are rejected", false,
    verifies(SECRET, replace_character(WRITE_SERVICE_IDENTIFIER, 10, ",")))

local own_mac = demo_visit_identifier.sign(SECRET, WRITE_SERVICE_NONCE, "1vuhmo0")
check("signing matches write-service byte for byte", WRITE_SERVICE_IDENTIFIER:sub(-22), own_mac)

check("constant_time_equals rejects a length mismatch", false,
    demo_visit_identifier.constant_time_equals("abc", "abcd"))

os.exit(failures == 0 and 0 or 1)
