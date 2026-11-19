local envelope      = require "power_finance.envelope"
local plugin_config = require "kong.plugins.demo-session.config"


local demo_session_invalid = function()
    return envelope.exit(
        401,
        plugin_config.DemoSessionInvalidCode,
        plugin_config.DemoSessionInvalidMessage
    )
end


return {
    demo_session_invalid = demo_session_invalid,
}
