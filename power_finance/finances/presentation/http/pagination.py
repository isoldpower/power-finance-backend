from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class StandardResultsPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100

    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'meta': {
                'limit': self.limit,
                'offset': self.offset,
                'total': self.count,
            }
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'data': schema,
                'meta': {
                    'type': 'object',
                    'properties': {
                        'limit': {
                            'type': 'integer',
                            'example': 10,
                            'description': 'Maximum number of items returned.'
                        },
                        'offset': {
                            'type': 'integer',
                            'example': 0,
                            'description': 'Number of items skipped.'
                        },
                        'total': {
                            'type': 'integer',
                            'example': 100,
                            'description': 'Total number of items available.'
                        },
                    },
                    'required': ['limit', 'offset', 'total'],
                    'description': 'Pagination metadata.'
                }
            },
            'required': ['data', 'meta']
        }