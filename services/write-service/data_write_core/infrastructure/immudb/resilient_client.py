import threading
from typing import Any

import grpc
from immudb import ImmudbClient


class ResilientImmudbClient:
    """Proxy around ImmudbClient that re-logins when the session token expires"""

    _EXPIRED_TOKEN_HINT = "token has expired"

    def __init__(
        self,
        client: ImmudbClient,
        username: str,
        password: str,
        database: str,
    ) -> None:
        self._client = client
        self._username = username
        self._password = password
        self._database = database
        self._relogin_lock = threading.Lock()

    def _is_expired_token(self, error: grpc.RpcError) -> bool:
        return error.code() == grpc.StatusCode.PERMISSION_DENIED and self._EXPIRED_TOKEN_HINT in (
            error.details() or ""
        )

    def _relogin(self) -> None:
        with self._relogin_lock:
            self._client.login(username=self._username, password=self._password)
            self._client.useDatabase(bytes(self._database, "utf-8"))

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if not callable(attr):
            return attr

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                return attr(*args, **kwargs)
            except grpc.RpcError as err:
                if not self._is_expired_token(err):
                    raise
                self._relogin()
                return getattr(self._client, name)(*args, **kwargs)

        return _wrapped
