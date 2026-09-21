from typing import NamedTuple

from ..sandbox import SandboxTrafficMatcher
from .kafka_message_context_binder import KafkaMessageContextBinder


class KafkaMessageContextComponents(NamedTuple):
    context_binder: KafkaMessageContextBinder
    traffic_policy: SandboxTrafficMatcher


def build_kafka_message_context_components() -> KafkaMessageContextComponents:
    return KafkaMessageContextComponents(
        context_binder=KafkaMessageContextBinder(),
        traffic_policy=SandboxTrafficMatcher.from_environment(),
    )
