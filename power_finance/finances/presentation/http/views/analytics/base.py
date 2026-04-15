from rest_framework.permissions import IsAuthenticated

from environment.presentation.http.base_api_view import BaseAPIView
from environment.presentation.middleware import AnalyticsThrottle


class AnalyticsView(BaseAPIView, AnalyticsThrottle):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AnalyticsThrottle]
    pagination_class = None
