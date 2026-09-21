-- The Read-At-Least header is what stops a client asserting any offset it
-- likes, so the signing helpers are the security boundary of this plugin.
local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local utilities = dofile(PLUGIN .. "/utilities.lua")

local failures = 0
local function check(label, condition, detail)
    if not condition then failures = failures + 1 end
    print((condition and "ok   " or "FAIL ") .. label .. (detail and ("  " .. detail) or ""))
end

local SECRET = "a-shared-secret-of-at-least-32-characters"

local digest, digest_error = utilities.retrieve_digest(SECRET, "42")
check("a digest is produced for a valid secret", digest ~= nil, tostring(digest_error))

local hex = utilities.to_hex(digest)
check("the digest encodes to 64 hex characters", #hex == 64, "len=" .. #hex)
check("the encoding is lowercase hex", hex:match("^[0-9a-f]+$") ~= nil, hex)

local repeated = utilities.to_hex(utilities.retrieve_digest(SECRET, "42"))
check("signing is deterministic", repeated == hex)

local other_offset = utilities.to_hex(utilities.retrieve_digest(SECRET, "43"))
check("a different offset signs differently", other_offset ~= hex)

local other_secret = utilities.to_hex(utilities.retrieve_digest(SECRET .. "x", "42"))
check("a different secret signs differently", other_secret ~= hex)

check("constant_time_equals accepts an exact match",
    utilities.constant_time_equals(hex, hex))
check("constant_time_equals rejects a differing digest",
    not utilities.constant_time_equals(hex, other_offset))
check("constant_time_equals rejects a length mismatch",
    not utilities.constant_time_equals(hex, hex:sub(1, 60)))
check("constant_time_equals rejects a non-string",
    not utilities.constant_time_equals(hex, nil))
check("constant_time_equals rejects two empty-vs-value",
    not utilities.constant_time_equals("", hex))

-- The header shape the handler accepts: `<offset>:<hex-hmac>`.
local HEADER_PATTERN = "^(%d+):([a-fA-F0-9]+)$"
local function parses(header)
    local offset, signature = header:match(HEADER_PATTERN)

    return offset ~= nil and signature ~= nil
end

check("a well-formed header parses", parses("42:" .. hex))
check("an uppercase signature parses", parses("42:" .. hex:upper()))
check("a header without a signature is rejected", not parses("42:"))
check("a header without an offset is rejected", not parses(":" .. hex))
check("a non-numeric offset is rejected", not parses("abc:" .. hex))
check("a non-hex signature is rejected", not parses("42:zzzz"))
check("a bare offset is rejected", not parses("42"))

os.exit(failures == 0 and 0 or 1)
