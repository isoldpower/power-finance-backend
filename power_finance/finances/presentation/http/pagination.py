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