local DEMO_SUBJECT_PREFIX = "demo_"


--- Whether a token subject belongs to a guest demo account rather than a Clerk user.
--
-- @param subject string|nil  the `sub` claim
-- @return boolean
local function is_demo_subject(subject)
    return type(subject) == "string"
        and #subject > #DEMO_SUBJECT_PREFIX
        and subject:sub(1, #DEMO_SUBJECT_PREFIX) == DEMO_SUBJECT_PREFIX
end


return {
    DEMO_SUBJECT_PREFIX = DEMO_SUBJECT_PREFIX,
    is_demo_subject = is_demo_subject,
}
