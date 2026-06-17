from rest_framework import status
from rest_framework.exceptions import APIException


class ReadModelNotCaughtUp(APIException):
    """Read side has not yet projected up to the client's Read-At-Least seq."""

    status_code = status.HTTP_507_INSUFFICIENT_STORAGE
    default_detail = "Read model has not caught up to the required write version."
    default_code = "read_model_not_caught_up"
