--- Map an inbound read path onto its Write Service fallback path by
--- swapping the leading prefix.
local build_fallback_path = function(path, read_prefix, fallback_prefix)
    if path:sub(1, #read_prefix) ~= read_prefix then
        return nil
    end

    return fallback_prefix .. path:sub(#read_prefix + 1)
end


--- Whether a forwarded response came from the API rather than the framework.
--
-- @param response table  resty.http response
-- @return boolean
local is_api_response = function(response)
    local content_type = response.headers and response.headers["Content-Type"]
    if type(content_type) == "table" then
        content_type = content_type[1]
    end

    return type(content_type) == "string"
        and content_type:lower():find("application/json", 1, true) == 1
end


return {
    build_fallback_path = build_fallback_path,
    is_api_response     = is_api_response,
}
