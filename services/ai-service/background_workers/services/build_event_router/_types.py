from dataclasses import dataclass

from kafka_consumer_py import HealthProbe
from service_core.shared.health_guard import PostgresHealthProbe


@dataclass
class ProbesDictionary:
    postgres_probe: HealthProbe

    @classmethod
    def build_probes(
        cls,
        postgres_probe: HealthProbe | None = None,
    ) -> "ProbesDictionary":
        return cls(postgres_probe=postgres_probe or PostgresHealthProbe())
