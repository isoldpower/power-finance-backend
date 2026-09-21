-- write-ral-version signs the offset that read-at-least later verifies, so the
-- two must agree byte for byte. Anything that drifts here fails open as a 401
-- on the read side, which reads like an auth problem rather than a signing one.
local PLUGIN = os.getenv("PLUGIN_DIR") or "/p"

local utilities = dofile(PLUGIN .. "/utilities.lua")

local failures = 0
local function check(label, condition, detail)
    if not condition then failures = failures + 1 end
    print((condition and "ok   " or "FAIL ") .. label .. (detail and ("  " .. detail) or ""))
end

local SECRET = "a-shared-secret-of-at-least-32-characters"

local digest, digest_error = utilities.retrieve_digest(SECRET, "7")
check("a digest is produced", digest ~= nil, tostring(digest_error))

local hex = utilities.to_hex(digest)
check("the digest encodes to 64 hex characters", #hex == 64, "len=" .. #hex)
check("the encoding is lowercase hex", hex:match("^[0-9a-f]+$") ~= nil, hex)
check("signing is deterministic", utilities.to_hex(utilities.retrieve_digest(SECRET, "7")) == hex)
check("a different offset signs differently",
    utilities.to_hex(utilities.retrieve_digest(SECRET, "8")) ~= hex)
check("a different secret signs differently",
    utilities.to_hex(utilities.retrieve_digest("another-secret-entirely-abcdefgh", "7")) ~= hex)

check("to_hex of an empty string is empty", utilities.to_hex("") == "")
check("to_hex pads single bytes to two characters", utilities.to_hex("\1\2") == "0102")
check("to_hex encodes high bytes", utilities.to_hex("\255") == "ff")

os.exit(failures == 0 and 0 or 1)
