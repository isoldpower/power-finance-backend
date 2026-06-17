local typedefs = require "kong.db.schema.typedefs"

return {
    name = "clerk-jwt",
    fields = {
        { consumer = typedefs.no_consumer },
        { protocols = typedefs.protocols_http },
        {
            config = {
                type = "record",
                fields = {
                    {
                        issuer_url = typedefs.url {
                            required = true,
                            referenceable = true,
                            description = [[
                                Clerk frontend API base URL. Plugin appends
                                /.well-known/jwks.json. Trailing slashes
                                are stripped automatically.
                            ]],
                        },
                    },
                    {
                        jwks_ttl_seconds = {
                            type = "number",
                            default = 300,
                            between = { 1, 86400 },
                            description = [[
                                How long to cache the JWKS response in Redis
                                before re-fetching.
                            ]],
                        },
                    },
                    {
                        http_timeout_ms = {
                            type = "number",
                            default = 5000,
                            between = { 100, 60000 },
                            description = [[
                                Timeout for the JWKS HTTP fetch.
                            ]],
                        },
                    },
                    {
                        clock_skew_seconds = {
                            type = "number",
                            default = 30,
                            between = { 0, 300 },
                            description = [[
                                Tolerance for `exp` claim comparison to
                                absorb minor clock drift between Clerk
                                and Kong.
                            ]],
                        },
                    },
                    {
                        allowed_azp_parties = {
                            type = "array",
                            elements = { type = "string" },
                            default = {},
                            description = [[
                                Allowed values for the `azp` (authorized
                                party) claim. Empty list disables the
                                check. Recommended in production to bind
                                tokens to a specific frontend origin.
                            ]],
                        },
                    },
                    {
                        redis_host = {
                            type = "string",
                            required = true,
                            description = "Redis host that caches the JWKS "
                                .. "document. Keyed by issuer URL so multiple "
                                .. "clerk-jwt instances can share the same "
                                .. "Redis without collision.",
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
                                .. "Redis. On Redis slowness the plugin "
                                .. "falls through to a fresh HTTP fetch "
                                .. "rather than 401'ing the request.",
                        },
                    },
                    {
                        redis_key_prefix = {
                            type = "string",
                            default = "clerk:jwks:",
                            description = "Prefix for the Redis key; the "
                                .. "issuer URL is appended verbatim.",
                        },
                    },
                },
            },
        },
    },
}
