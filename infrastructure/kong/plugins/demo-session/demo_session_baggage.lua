local plugin_config = require "kong.plugins.demo-session.config"


local is_valid_demo_session_identifier = function(candidate_identifier)
    if type(candidate_identifier) ~= "string" then
        return false
    end

    local identifier_length = #candidate_identifier
    if identifier_length < plugin_config.DemoSessionIdentifierMinimumSize
        or identifier_length > plugin_config.DemoSessionIdentifierMaximumSize then
        return false
    end

    return candidate_identifier:match("^[%w_%-]+$") ~= nil
end


local read_demo_session_identifier = function(header_name)
    local candidate_identifier = kong.request.get_header(header_name)
    if not is_valid_demo_session_identifier(candidate_identifier) then
        return nil
    end

    return candidate_identifier
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
    is_valid_demo_session_identifier = is_valid_demo_session_identifier,
    read_demo_session_identifier     = read_demo_session_identifier,
    replace_baggage_entry            = replace_baggage_entry,
    propagate_demo_session           = propagate_demo_session,
}
