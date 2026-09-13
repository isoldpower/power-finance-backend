local sandbox_routes = require "power_finance.sandbox_routes"


local get_sandbox_target = function(config, sandbox_id, service_name)
    return sandbox_routes.resolve_target(config, sandbox_id, service_name)
end


local exports = {
    get_sandbox_target = get_sandbox_target,
}

return exports
