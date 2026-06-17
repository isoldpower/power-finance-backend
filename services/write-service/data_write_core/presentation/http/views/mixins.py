from rest_framework.response import Response


class CommandResponseMixin:
    def form_write_response(
        self,
        write_version: int,
        response_body: dict,
        status_code: int,
    ):
        response = Response(
            response_body,
            status=status_code,
            headers={
                "X-Write-Version": str(write_version),
            },
        )

        return response
