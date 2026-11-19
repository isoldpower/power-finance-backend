local plugin_config = require "kong.plugins.demo-session.config"


local read_presented_identifiers = function(header_name, query_parameter_name)
    local presented_identifiers = {}

    local header_identifier = header_name and kong.request.get_header(header_name)
    if header_identifier ~= nil and header_identifier ~= "" then
        presented_identifiers[#presented_identifiers + 1] = header_identifier
    end

    local query_identifier = query_parameter_name and kong.request.get_query_arg(query_parameter_name)
    if query_identifier ~= nil and query_identifier ~= "" then
        presented_identifiers[#presented_identifiers + 1] = query_identifier
    end

    return presented_identifiers
end


local replace_baggage_entry = function(baggage_header_value, entry_name, entry_value)
    local retained_entries = {}
    if type(baggage_header_value) == "string" then
        for entry in baggage_header_value:gmatch("[^,]+") do
            local candidate_name = entry:match("^%s*([^=%s]+)")
            if candidate_name and candidate_name ~= entry_name then
                retained_entries[#retained_entries + 1] = entry:match("^%s*(.-)%s*$")
            end
        end
    end

    retained_entries[#retained_entries + 1] = entry_name .. "=" .. entry_value

    return table.concat(retained_entries, ",")
end


local propagate_demo_session = function(demo_session_identifier)
    kong.service.request.set_header(
        plugin_config.BaggageHeader,
        replace_baggage_entry(
            kong.request.get_header(plugin_config.BaggageHeader),
            plugin_config.DemoSessionBaggageEntry,
            demo_session_identifier
        )
    )
end


return {
    read_presented_identifiers = read_presented_identifiers,
    replace_baggage_entry      = replace_baggage_entry,
    propagate_demo_session     = propagate_demo_session,
}
