local typedefs = require "kong.db.schema.typedefs"

return {
    name = "demo-session",
    fields = {
        { consumer = typedefs.no_consumer },
        { protocols = typedefs.protocols_http },
        {
            config = {
                type = "record",
                fields = {
                    {
                        header_name = {
                            type = "string",
                            default = "X-Demo-Session",
                            description = "Request header carrying the portfolio demo "
                                .. "session identifier.",
                        },
                    },
                    {
                        force_sampling = {
                            type = "boolean",
                            default = true,
                            description = "Sample every trace of a demo session "
                                .. "regardless of the gateway sampling rate.",
                        },
                    },
                },
            },
        },
    },
}
