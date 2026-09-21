local read_entry = function(baggage_header_value, entry_name)
    if type(baggage_header_value) ~= "string" or baggage_header_value == "" then
        return nil
    end

    for entry in baggage_header_value:gmatch("[^,]+") do
        local candidate_name, candidate_value = entry:match("^%s*([^=%s]+)%s*=%s*([^;]*)")
        if candidate_name == entry_name then
            local trimmed_value = (candidate_value or ""):gsub("%s+$", "")
            if trimmed_value ~= "" then
                return trimmed_value
            end

            return nil
        end
    end

    return nil
end


local append_entry = function(baggage_header_value, entry_name, entry_value)
    local new_entry = entry_name .. "=" .. entry_value
    if type(baggage_header_value) ~= "string" or baggage_header_value == "" then
        return new_entry
    end

    return baggage_header_value .. "," .. new_entry
end


local exports = {
    read_entry   = read_entry,
    append_entry = append_entry,
}

return exports
