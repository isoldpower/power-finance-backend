local BAGGAGE_HEADER_NAME = "baggage"
local DEMO_SESSION_BAGGAGE_ENTRY_NAME = "demo-session"
local DEMO_SESSION_SPAN_ATTRIBUTE_NAME = "demo-session"
local DEMO_SESSION_IDENTIFIER_MINIMUM_LENGTH = 16
local DEMO_SESSION_IDENTIFIER_MAXIMUM_LENGTH = 64


return {
    BaggageHeader                    = BAGGAGE_HEADER_NAME,
    DemoSessionBaggageEntry          = DEMO_SESSION_BAGGAGE_ENTRY_NAME,
    DemoSessionSpanAttribute         = DEMO_SESSION_SPAN_ATTRIBUTE_NAME,
    DemoSessionIdentifierMinimumSize = DEMO_SESSION_IDENTIFIER_MINIMUM_LENGTH,
    DemoSessionIdentifierMaximumSize = DEMO_SESSION_IDENTIFIER_MAXIMUM_LENGTH,
}
