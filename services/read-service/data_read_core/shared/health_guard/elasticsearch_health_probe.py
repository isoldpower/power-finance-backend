from elastic_transport import TransportError

from data_read_core.shared.elasticsearch import get_elasticsearch

from .health_probe import HealthProbe

ELASTICSEARCH_CONNECTIVITY_ERRORS: tuple[type[BaseException], ...] = (
    TransportError,
    OSError,
)


class ElasticsearchHealthProbe(HealthProbe):
    """`HealthProbe` backed by an Elasticsearch ping."""

    @property
    def name(self) -> str:
        return "elasticsearch"

    async def is_healthy(self) -> bool:
        try:
            return bool(await get_elasticsearch().ping())
        except ELASTICSEARCH_CONNECTIVITY_ERRORS:
            return False
