local typedefs = require "kong.db.schema.typedefs"

return {
    name = "sandbox-router",
    fields = {
        { consumer = typedefs.no_consumer },
        { protocols = typedefs.protocols_http },
        {
            config = {
                type = "record",
                fields = {
                    {
                        redis_host = {
                            type = "string",
                            required = true,
                            description = "Redis host holding sandbox routes under "
                                .. "`{redis_key_prefix}{sandbox_id}`, each value a "
                                .. "`host:port` upstream. Same instance the "
                                .. "read-at-least plugins use.",
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
                            description = "Connect / read / send timeout for Redis. "
                                .. "Kept tight on purpose — on Redis slowness the "
                                .. "plugin fails open and the request goes to the "
                                .. "baseline upstream rather than blocking.",
                        },
                    },
                    {
                        redis_key_prefix = {
                            type = "string",
                            default = "sandbox:route:",
                            description = "Key namespace; the sandbox id is appended "
                                .. "verbatim. Must match what `make sandbox-up` writes.",
                        },
                    },
                    {
                        propagate_baggage = {
                            type = "boolean",
                            default = true,
                            description = "When the sandbox id arrived in the "
                                .. "X-Sandbox header rather than in W3C baggage, "
                                .. "add it to the baggage header so downstream "
                                .. "services and Kafka consumers see it too.",
                        },
                    },
                },
            },
        },
    },
}
