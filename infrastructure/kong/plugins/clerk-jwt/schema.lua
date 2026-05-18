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
                        issuer_url = {
                            type = "string",
                            required = true,
                            description = "Clerk frontend API base URL (no trailing slash). "
                                .. "Plugin appends /.well-known/jwks.json.",
                        },
                    },
                    {
                        jwks_ttl_seconds = {
                            type = "number",
                            default = 300,
                            description = "How long to cache the JWKS response in the "
                                .. "shared dict before re-fetching.",
                        },
                    },
                    {
                        http_timeout_ms = {
                            type = "number",
                            default = 5000,
                            description = "Timeout for the JWKS HTTP fetch.",
                        },
                    },
                },
            },
        },
    },
}
