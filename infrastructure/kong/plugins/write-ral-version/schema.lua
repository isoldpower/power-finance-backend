local typedefs = require "kong.db.schema.typedefs"

return {
    name = "write-ral-version",
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
                                .. "by the read-at-least plugin so signatures "
                                .. "produced here verify there.",
                        },
                    },
                    {
                        write_version_header = {
                            type = "string",
                            default = "X-Write-Version",
                            description = "Response header carrying the raw "
                                .. "outbox seq from upstream. Rewritten in "
                                .. "place with the signed `{seq}:{hmac}` form.",
                        },
                    },
                    {
                        redis_host = {
                            type = "string",
                            required = true,
                            description = "Redis host that stores per-user "
                                .. "latest outbox seq under "
                                .. "`{redis_key_prefix}{sub}`. Same instance "
                                .. "and prefix as the read-at-least plugin.",
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
                                .. "slowness the plugin fails open (no offset "
                                .. "recorded) rather than delaying the write "
                                .. "response that has already been sent.",
                        },
                    },
                    {
                        redis_key_prefix = {
                            type = "string",
                            default = "ral:user:",
                            description = "Key namespace; user id is appended "
                                .. "verbatim. Must match read-at-least.",
                        },
                    },
                    {
                        redis_ttl_seconds = {
                            type = "number",
                            default = 604800,
                            between = { 60, 2592000 },
                            description = "TTL applied to each per-user offset "
                                .. "entry on every monotonic write. Default 7 "
                                .. "days; inactive users drop out of Redis "
                                .. "automatically.",
                        },
                    },
                },
            },
        },
    },
}
