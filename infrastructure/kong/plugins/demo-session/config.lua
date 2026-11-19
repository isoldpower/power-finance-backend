local BAGGAGE_HEADER_NAME = "baggage"
local DEMO_SESSION_BAGGAGE_ENTRY_NAME = "demo-session"
local DEMO_SESSION_SPAN_ATTRIBUTE_NAME = "demo-session"
local DEMO_VISIT_IDENTIFIER_VERSION = "dv1"
local DEMO_VISIT_NONCE_LENGTH = 22
local DEMO_VISIT_MAC_LENGTH = 22
local DEMO_VISIT_MAC_BYTES = 16
local DEMO_VISIT_EXPIRY_MAXIMUM_LENGTH = 13
local DEMO_VISIT_IDENTIFIER_MAXIMUM_LENGTH = 64
local DEMO_SESSION_INVALID_CODE = "demo_session_invalid"
local DEMO_SESSION_INVALID_MESSAGE = "Demo session is invalid or expired."


return {
    BaggageHeader                   = BAGGAGE_HEADER_NAME,
    DemoSessionBaggageEntry         = DEMO_SESSION_BAGGAGE_ENTRY_NAME,
    DemoSessionSpanAttribute        = DEMO_SESSION_SPAN_ATTRIBUTE_NAME,
    DemoVisitIdentifierVersion      = DEMO_VISIT_IDENTIFIER_VERSION,
    DemoVisitNonceLength            = DEMO_VISIT_NONCE_LENGTH,
    DemoVisitMacLength              = DEMO_VISIT_MAC_LENGTH,
    DemoVisitMacBytes               = DEMO_VISIT_MAC_BYTES,
    DemoVisitExpiryMaximumLength    = DEMO_VISIT_EXPIRY_MAXIMUM_LENGTH,
    DemoVisitIdentifierMaximumSize  = DEMO_VISIT_IDENTIFIER_MAXIMUM_LENGTH,
    DemoSessionInvalidCode          = DEMO_SESSION_INVALID_CODE,
    DemoSessionInvalidMessage       = DEMO_SESSION_INVALID_MESSAGE,
}
