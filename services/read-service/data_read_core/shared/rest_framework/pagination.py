from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class StandardResultsPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "data": data,
                "meta": {
                    "limit": self.limit,
                    "offset": self.offset,
                    "total": self.count,
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "data": schema,
                "meta": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "example": 20,
                        },
                        "offset": {
                            "type": "integer",
                            "example": 0,
                        },
                        "total": {
                            "type": "integer",
                            "example": 100,
                        },
                    },
                    "required": ["limit", "offset", "total"],
                },
            },
            "required": ["data", "meta"],
        }
