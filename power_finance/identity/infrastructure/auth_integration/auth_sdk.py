from abc import ABC, abstractmethod

from identity.application.dto import ExternalUserInfo


class AuthSdk(ABC):
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
