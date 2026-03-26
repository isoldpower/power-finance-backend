from functools import wraps

from .use_case_base import UseCaseEvently
from ..bootstrap import get_event_bus


def handle_evently_command(function):
    @wraps(function)
    def with_event_publish(
            self: UseCaseEvently,
            *args,
            **kwargs
    ):
        result = function(self, *args, **kwargs)

        recorded_events = self.event_collector.pull_events()
        get_event_bus().publish(recorded_events)
        return result

    return with_event_publish

