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


return {
    force_trace_sampling = force_trace_sampling,
}
