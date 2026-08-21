local typedefs = require "kong.db.schema.typedefs"

return {
    name = "read-fallback",
    fields = {
        { consumer = typedefs.no_consumer },
        { protocols = typedefs.protocols_http },
        {
            config = {
                type = "record",
                fields = {
                    {
                        read_service_url = {
                            type = "string",
                            required = true,
                            description = "Base URL of the Read Service "
                                .. "(scheme + host + port, no trailing slash), "
                                .. "e.g. http://read-service:8000. The plugin "
                                .. "proxies the read here itself so it can "
                                .. "observe the status synchronously.",
                        },
                    },
                    {
                        write_service_url = {
                            type = "string",
                            required = true,
                            description = "Base URL of the Write Service whose "
                                .. "fallback-read endpoints serve the "
                                .. "always-consistent answer, e.g. "
                                .. "http://write-service:8000.",
                        },
                    },
                    {
                        read_path_prefix = {
                            type = "string",
                            default = "/api/v1",
                            description = "Inbound read path prefix; replaced "
                                .. "with fallback_path_prefix when building the "
                                .. "Write Service fallback URL.",
                        },
                    },
                    {
                        fallback_path_prefix = {
                            type = "string",
                            default = "/api/v1/fallback-reads",
                            description = "Path prefix the Write Service serves "
                                .. "its consistent fallback reads under.",
                        },
                    },
                    {
                        fallback_status = {
                            type = "number",
                            default = 507,
                            between = { 400, 599 },
                            description = "Read Service status that triggers the "
                                .. "fallback. 507 means the projection is behind "
                                .. "the client's Read-At-Least; any other status "
                                .. "is returned to the client verbatim.",
                        },
                    },
                    {
                        read_timeout_ms = {
                            type = "number",
                            default = 10000,
                            between = { 1, 600000 },
                            description = "Connect/send/read timeout for the "
                                .. "primary Read Service call.",
                        },
                    },
                    {
                        fallback_timeout_ms = {
                            type = "number",
                            default = 30000,
                            between = { 1, 600000 },
                            description = "Timeout for the Write Service fallback "
                                .. "call. Larger than read_timeout_ms — the "
                                .. "fallback folds the ImmuDB ledger and is "
                                .. "deliberately slower but consistent.",
                        },
                    },
                },
            },
        },
    },
}
