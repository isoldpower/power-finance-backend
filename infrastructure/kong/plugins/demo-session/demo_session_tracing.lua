local plugin_config         = require "kong.plugins.demo-session.config"
local gateway_trace_context = require "power_finance.gateway_trace_context"


local force_trace_sampling = function(demo_session_identifier)
    local root_span = gateway_trace_context.read_root_span()
    if not root_span then
        return
    end

    root_span:set_attribute(plugin_config.DemoSessionSpanAttribute, demo_session_identifier)
    kong.tracing:set_should_sample(true)
end


local tag_request_spans = function(request_spans, demo_session_identifier)
    for _, request_span in ipairs(request_spans or {}) do
        request_span:set_attribute(plugin_config.DemoSessionSpanAttribute, demo_session_identifier)
    end
end


return {
    force_trace_sampling = force_trace_sampling,
    tag_request_spans    = tag_request_spans,
}
