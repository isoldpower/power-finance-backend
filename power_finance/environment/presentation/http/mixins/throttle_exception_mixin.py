from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework import status


class ThrottleExceptionMixin:
    def handle_exception(self, exc):
        if isinstance(exc, Throttled):
            retry_after = int(exc.wait) if exc.wait is not None else None
            data = {
                'error': 'rate_limit_exceeded',
                'message': f'Too many requests. Retry after {retry_after} seconds.',
                'retry_after': retry_after,
            }
            response = Response(data, status=status.HTTP_429_TOO_MANY_REQUESTS)
            if retry_after is not None:
                response['Retry-After'] = str(retry_after)
            return response
        return super().handle_exception(exc)
