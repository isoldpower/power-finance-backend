from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_query_param = 'page'

    def get_paginated_response(self, data):
        offset = (self.page.number - 1) * self.page_size

        return Response({
            'data': data,
            'meta': {
                'limit': self.page_size,
                'offset': offset,
                'total': self.page.paginator.count,
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