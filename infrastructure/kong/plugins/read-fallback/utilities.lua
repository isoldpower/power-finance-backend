--- Map an inbound read path onto its Write Service fallback path by
-- swapping the leading prefix. Returns nil when the path does not start
-- with the configured read prefix (nothing to map).
local build_fallback_path = function(path, read_prefix, fallback_prefix)
    if path:sub(1, #read_prefix) ~= read_prefix then
        return nil
    end

    return fallback_prefix .. path:sub(#read_prefix + 1)
end


return {
    build_fallback_path = build_fallback_path
}
