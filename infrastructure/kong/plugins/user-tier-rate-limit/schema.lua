local typedefs = require "kong.db.schema.typedefs"

return {
    name = "user-tier-rate-limit",
    fields = {
        { consumer = typedefs.no_consumer },
        { protocols = typedefs.protocols_http },
        {
            config = {
                type = "record",
                fields = {
                    {
                        per_minute = {
                            type = "number",
                            required = true,
                            gt = 0,
                            description = "Authenticated-user request cap per "
                                .. "minute (fixed window). Looser than the IP "
                                .. "floor that applies to everyone.",
                        },
                    },
                    {
                        per_hour = {
                            type = "number",
                            required = true,
                            gt = 0,
                            description = "Authenticated-user request cap per hour.",
                        },
                    },
                    {
                        redis_host = {
                            type = "string",
                            default = "gateway-redis",
                        },
                    },
                    { redis_port = { type = "number", default = 6379 } },
                    { redis_database = { type = "number", default = 0 } },
                    {
                        redis_password = {
                            type = "string",
                            referenceable = true,
                            required = false,
                        },
                    },
                    {
                        redis_timeout_ms = {
                            type = "number",
                            default = 1000,
                            description = "Connect + read + write timeout. "
                                .. "Plugin fails open on timeout.",
                        },
                    },
                },
            },
        },
    },
}
