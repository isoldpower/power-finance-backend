local demo_session_baggage  = require "kong.plugins.demo-session.demo_session_baggage"
local demo_session_tracing  = require "kong.plugins.demo-session.demo_session_tracing"
local demo_visit_identifier = require "kong.plugins.demo-session.demo_visit_identifier"
local messages              = require "kong.plugins.demo-session.messages"

local DemoSessionHandler = {
    PRIORITY = 740,
    VERSION  = "0.3.0",
}


local verify_presented_identifiers = function(config, presented_identifiers)
    local current_unix_seconds = ngx.time()
    for _, presented_identifier in ipairs(presented_identifiers) do
        local verified_visit, rejection_reason = demo_visit_identifier.verify(
            config.secret,
            presented_identifier,
            current_unix_seconds
        )
        if not verified_visit then
            kong.log.info("demo-session: rejected identifier: ", rejection_reason)
            return false
        end
    end

    return true
end


function DemoSessionHandler:access(config)
    local presented_identifiers = demo_session_baggage.read_presented_identifiers(
        config.header_name,
        config.query_parameter_name
    )
    if #presented_identifiers == 0 then
        if config.required then
            return messages.demo_session_invalid()
        end
        return
    end

    if not verify_presented_identifiers(config, presented_identifiers) then
        if config.required or config.reject_invalid then
            return messages.demo_session_invalid()
        end
        return
    end

    if not config.trace_request then
        return
    end

    local demo_session_identifier = presented_identifiers[1]
    kong.ctx.plugin.demo_session_identifier = demo_session_identifier
    demo_session_baggage.propagate_demo_session(demo_session_identifier)

    if config.force_sampling then
        demo_session_tracing.force_trace_sampling(demo_session_identifier)
    end
end


function DemoSessionHandler:log(config)
    local demo_session_identifier = kong.ctx.plugin.demo_session_identifier
    if not demo_session_identifier then
        return
    end

    demo_session_tracing.tag_request_spans(ngx.ctx.KONG_SPANS, demo_session_identifier)
end


return DemoSessionHandler
