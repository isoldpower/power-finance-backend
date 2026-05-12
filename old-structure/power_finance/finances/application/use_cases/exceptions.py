class IdempotencyInFlightError(Exception):
    pass


class IdempotencyCachedError(Exception):
    def __init__(self, payload: str):
        self.payload = payload