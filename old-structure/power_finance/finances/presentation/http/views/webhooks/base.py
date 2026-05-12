from rest_framework.permissions import IsAuthenticated

from environment.presentation.http.base_api_view import BaseAPIView
from environment.presentation.middleware import WebhookRegistrationThrottle
from finances.presentation.http.pagination import StandardResultsPagination


class WebhookView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [WebhookRegistrationThrottle]
    pagination_class = StandardResultsPagination