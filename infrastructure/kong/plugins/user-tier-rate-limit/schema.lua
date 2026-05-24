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
                            description = "Authenticated-user request cap per "
                                .. "hour (fixed window).",
                        },
                    },
                    {
                        redis_host = {
                            type = "string",
                            required = true,
                            description = "Redis host that stores per-user "
                                .. "window counters. Same instance used by the "
                                .. "other custom plugins is fine — key "
                                .. "namespaces do not collide.",
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
                            default = 1000,
                            between = { 1, 60000 },
                            description = "Connect / read / send timeout for "
                                .. "Redis. On timeout the plugin fails open "
                                .. "and the request proceeds without being "
                                .. "counted; the IP floor still bounds the "
                                .. "blast radius.",
                        },
                    },
                    {
                        redis_key_prefix = {
                            type = "string",
                            default = "rl:user:",
                            description = "Key namespace; user id, window "
                                .. "label, and bucket epoch are appended to "
                                .. "form the full counter key.",
                        },
                    },
                },
            },
        },
    },
}
