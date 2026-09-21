class UnknownUserError(Exception):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"user {user_id} has no known external id")

        self.user_id = user_id
