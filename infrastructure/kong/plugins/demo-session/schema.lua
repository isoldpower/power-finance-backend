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
                        secret = {
                            type = "string",
                            required = false,
                            referenceable = true,
                            description = "HMAC-SHA256 secret shared with write-service, "
                                .. "which issues the demo visit identifiers. Without it "
                                .. "every presented identifier is rejected.",
                        },
                    },
                    {
                        header_name = {
                            type = "string",
                            default = "X-Demo-Session",
                            description = "Request header carrying the demo visit identifier.",
                        },
                    },
                    {
                        query_parameter_name = {
                            type = "string",
                            required = false,
                            description = "Query parameter that may also carry the identifier, "
                                .. "for clients that cannot set headers (WebSocket, EventSource). "
                                .. "Every presented identifier must verify.",
                        },
                    },
                    {
                        required = {
                            type = "boolean",
                            default = false,
                            description = "Reject a request that presents no identifier.",
                        },
                    },
                    {
                        reject_invalid = {
                            type = "boolean",
                            default = true,
                            description = "Reject a request whose identifier is forged, "
                                .. "tampered with or expired. When false the identifier "
                                .. "is ignored instead.",
                        },
                    },
                    {
                        trace_request = {
                            type = "boolean",
                            default = true,
                            description = "Put a verified identifier into the upstream "
                                .. "baggage and onto the gateway spans.",
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
