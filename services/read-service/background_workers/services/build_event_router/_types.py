from dataclasses import dataclass

from data_read_core.shared.health_guard import (
    ElasticsearchHealthProbe,
    HealthProbe,
    PostgresHealthProbe,
    RedisHealthProbe,
)


@dataclass
class ProbesDictionary:
    postgres_probe: HealthProbe
    redis_probe: HealthProbe
    elasticsearch_probe: HealthProbe

    @classmethod
    def build_probes(
        cls,
        postgres_probe: HealthProbe | None = None,
        redis_probe: HealthProbe | None = None,
        elasticsearch_probe: HealthProbe | None = None,
    ) -> "ProbesDictionary":
        return cls(
            postgres_probe=postgres_probe or PostgresHealthProbe(),
            redis_probe=redis_probe or RedisHealthProbe(),
            elasticsearch_probe=elasticsearch_probe or ElasticsearchHealthProbe(),
        )
