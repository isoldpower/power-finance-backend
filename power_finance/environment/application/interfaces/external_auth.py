from abc import ABC, abstractmethod

from environment.application.dtos import ExternalUserInfo


class ExternalAuth(ABC):
    @abstractmethod
    def resolve_auth_token(self, received_header: str) -> str | None:
        """
        Parses authorization header into final token view
        :param received_header: Authorization token header attached to the request
        :return: Raw authorization token
        """
        raise NotImplementedError()

    @abstractmethod
    def fetch_user_info(self, user_id: str) -> ExternalUserInfo | None:
        """
        Method used to fetch user information from Provider's service based on user id

        Arguments:
            user_id: Unique identifier of the user
        Returns:
            tuple[dict, bool] where first argument is user's information and second argument is whether
            user was authenticated
        """
        raise NotImplementedError()

    @abstractmethod
    def get_jwks(self) -> dict:
        """
        Method used to fetch JWKS to decode user info from Provider's service

        Returns:
            dict representing user's JWKS to decode user info from Provider's service
        """
        raise NotImplementedError()