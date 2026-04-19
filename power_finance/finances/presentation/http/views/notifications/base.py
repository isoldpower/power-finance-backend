from rest_framework.permissions import IsAuthenticated

from environment.presentation.http.base_api_view import BaseAPIView

from ...pagination import StandardResultsPagination


class NotificationView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination
