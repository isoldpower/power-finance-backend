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
                            description = "Shared HMAC-SHA256 secret. Write Service "
                                .. "signs offsets with the same secret when returning "
                                .. "X-Write-Version to clients; gateway verifies on "
                                .. "subsequent reads.",
                        },
                    },
                    {
                        offset_claim_name = {
                            type = "string",
                            default = "last_write_offset",
                            description = "JWT claim that carries the user's default "
                                .. "read offset. When Read-At-Least header is absent, "
                                .. "the plugin signs this claim's value and injects "
                                .. "the header.",
                        },
                    },
                },
            },
        },
    },
}
