local resty_string = require "resty.string"


local TRACEPARENT_FORMAT = "00-%s-%s-%s"
local SAMPLED_FLAGS = "01"
local UNSAMPLED_FLAGS = "00"
local PROPAGATION_ONLY_ATTRIBUTE = "kong.propagation_only"


local read_root_span = function()
    local root_span = ngx.ctx.KONG_SPANS and ngx.ctx.KONG_SPANS[1]
    if not root_span or not root_span.trace_id or not root_span.span_id then
        return nil
    end

    if root_span.attributes and root_span.attributes[PROPAGATION_ONLY_ATTRIBUTE] then
        return nil
    end

    return root_span
end


local build_root_traceparent = function()
    local root_span = read_root_span()
    if not root_span then
        return nil
    end

    return string.format(
        TRACEPARENT_FORMAT,
        resty_string.to_hex(root_span.trace_id),
        resty_string.to_hex(root_span.span_id),
        root_span.should_sample and SAMPLED_FLAGS or UNSAMPLED_FLAGS
    )
end


return {
    read_root_span         = read_root_span,
    build_root_traceparent = build_root_traceparent,
}
