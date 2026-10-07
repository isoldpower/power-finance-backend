local demo_session_baggage = require "kong.plugins.demo-session.demo_session_baggage"
local demo_session_tracing = require "kong.plugins.demo-session.demo_session_tracing"

local DemoSessionHandler = {
    PRIORITY = 740,
    VERSION  = "0.1.0",
}


function DemoSessionHandler:access(config)
    local demo_session_identifier = demo_session_baggage.read_demo_session_identifier(
        config.header_name
    )
    if not demo_session_identifier then
        return
    end

    demo_session_baggage.propagate_demo_session(demo_session_identifier)

    if config.force_sampling then
        demo_session_tracing.force_trace_sampling(demo_session_identifier)
    end
end


return DemoSessionHandler
