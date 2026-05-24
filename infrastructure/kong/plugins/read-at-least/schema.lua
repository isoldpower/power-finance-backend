local typedefs = require "kong.db.schema.typedefs"

return {
    name = "read-at-least",
    fields = {
        { consumer = typedefs.no_consumer },
        { protocols = typedefs.protocols_http },
        {
            config = {
                type = "record",
                fields = {
                    {
                        hmac_secret = {
                            type = "string",
                            required = true,
                            referenceable = true,
                            len_min = 32,
                            description = "Gateway-internal HMAC-SHA256 secret "
                                .. "(>= 32 bytes). Must match the secret used "
                                .. "by the write-ral-version plugin so signatures "
                                .. "produced there verify here.",
                        },
                    },
                    {
                        redis_host = {
                            type = "string",
                            required = true,
                            description = "Redis host that stores per-user "
                                .. "latest outbox seq under "
                                .. "`{redis_key_prefix}{sub}`. Same instance "
                                .. "and prefix as the write-ral-version plugin.",
                        },
                    },
                    {
                        redis_port = {
                            type = "number",
                            default = 6379,
                            between = { 1, 65535 },
                            description = "Redis port.",
                        },
                    },
                    {
                        redis_database = {
                            type = "number",
                            default = 0,
                            between = { 0, 15 },
                            description = "Redis logical database index.",
                        },
                    },
                    {
                        redis_password = {
                            type = "string",
                            referenceable = true,
                            description = "Optional Redis AUTH password.",
                        },
                    },
                    {
                        redis_timeout_ms = {
                            type = "number",
                            default = 100,
                            between = { 1, 60000 },
                            description = "Connect / read / send timeout for "
                                .. "Redis. Kept tight on purpose — on Redis "
                                .. "slowness the plugin fails open and the "
                                .. "read proceeds without a header rather "
                                .. "than blocking the request.",
                        },
                    },
                    {
                        redis_key_prefix = {
                            type = "string",
                            default = "ral:user:",
                            description = "Key namespace; user id is appended "
                                .. "verbatim. Must match write-ral-version.",
                        },
                    },
                },
            },
        },
    },
}
