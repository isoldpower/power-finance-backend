class IdempotencyInFlightError(Exception):
    pass


class IdempotencyCachedError(Exception):
    def __init__(self, payload: bytes):
        self.payload = payload