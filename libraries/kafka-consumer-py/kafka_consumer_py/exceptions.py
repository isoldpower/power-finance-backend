class EventRouterError(Exception):
    pass


class HandlerNotFoundError(EventRouterError):
    pass


class EnvelopeError(ValueError):
    pass


class MalformedEnvelope(EnvelopeError):
    pass
