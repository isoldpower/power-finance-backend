import httpx
import requests

from finances.application.interfaces import NetworkSender, MessageResponse


class HttpSender(NetworkSender):
    async def send_message_with_body(
            self,
            url: str,
            request_body: dict,
            request_headers: dict,
    ) -> MessageResponse:
        try:
            async with httpx.AsyncClient() as client:
                response: requests.Response = await client.post(
                    url=url,
                    data=request_body,
                    headers=request_headers,
                    timeout=5,
                    follow_redirects=False,
                )

                return MessageResponse(
                    status_code=response.status_code,
                    response_body=response.text,
                    response_headers=request_headers,
                    error_message=None,
                )
        except httpx.NetworkError:
            return MessageResponse(
                status_code=500,
                response_body="Connection refused",
                response_headers=None,
                error_message="Connection refused",
            )
        except httpx.TimeoutException:
            return MessageResponse(
                status_code=500,
                response_body="Timeout error",
                response_headers=request_headers,
                error_message="Timeout error",
            )
        except httpx.TooManyRedirects:
            return MessageResponse(
                status_code=500,
                response_body="TooManyRedirects",
                response_headers=request_headers,
                error_message="TooManyRedirects",
            )
        except httpx.RequestError:
            return MessageResponse(
                status_code=500,
                response_body="Request failed",
                response_headers=request_headers,
                error_message="Request failed with unknown error",
            )
        except Exception:
            return MessageResponse(
                status_code=500,
                response_body="Internal error",
                response_headers=request_headers,
                error_message="Internal error",
            )
