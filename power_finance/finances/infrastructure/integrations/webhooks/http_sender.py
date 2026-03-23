import json
import requests

from finances.application.interfaces import NetworkSender, MessageResponse


class HttpSender(NetworkSender):
    def send_message_with_body(
            self,
            url: str,
            request_body: dict,
            request_headers: dict,
    ) -> MessageResponse:
        try:
            response: requests.Response = requests.post(
                url=url,
                data=json.dumps(request_body),
                headers=request_headers,
                timeout=5,
                allow_redirects=False,
                verify=True,
            )

            return MessageResponse(
                status_code=response.status_code,
                response_body=response.text,
                response_headers=request_headers,
                error_message=None,
            )
        except requests.exceptions.ConnectionError:
            return MessageResponse(
                status_code=500,
                response_body="Connection refused",
                response_headers=request_headers,
                error_message="Connection refused",
            )
        except requests.exceptions.Timeout:
            return MessageResponse(
                status_code=500,
                response_body="Timeout error",
                response_headers=request_headers,
                error_message="Timeout error",
            )
        except requests.exceptions.TooManyRedirects:
            return MessageResponse(
                status_code=500,
                response_body="TooManyRedirects",
                response_headers=request_headers,
                error_message="TooManyRedirects",
            )
        except requests.exceptions.RequestException:
            return MessageResponse(
                status_code=500,
                response_body="Request failed",
                response_headers=request_headers,
                error_message="Request failed with unknown error",
            )
