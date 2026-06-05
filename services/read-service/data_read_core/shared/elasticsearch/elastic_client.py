from functools import lru_cache

from django.conf import settings
from elasticsearch import AsyncElasticsearch


@lru_cache(maxsize=1)
def get_elasticsearch() -> AsyncElasticsearch:
    """Return the process-wide async Elasticsearch client."""

    client_kwargs: dict = {
        "hosts": settings.ELASTICSEARCH["HOSTS"],
        "basic_auth": (
            settings.ELASTICSEARCH["USERNAME"],
            settings.ELASTICSEARCH["PASSWORD"],
        ),
        "verify_certs": settings.ELASTICSEARCH["VERIFY_CERTS"],
    }

    ca_certs = settings.ELASTICSEARCH["CA_CERTS"]
    if ca_certs:
        client_kwargs["ca_certs"] = ca_certs

    return AsyncElasticsearch(**client_kwargs)
