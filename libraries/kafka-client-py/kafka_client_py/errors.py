class KafkaHandlerError(Exception):
    pass


class TransientError(Exception):
    pass


class PoisonError(Exception):
    pass


class RetryExhaustedError(KafkaHandlerError):
    pass
