from rest_framework.views import APIView

from .mixins import ThrottleHeadersMixin, ThrottleExceptionMixin


class BaseAPIView(ThrottleExceptionMixin, ThrottleHeadersMixin, APIView):
    pass
