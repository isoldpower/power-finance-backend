class DjangoInstrumentationActivator:
    instrumentation_name = "django"

    def activate(self) -> None:
        from opentelemetry.instrumentation.django import DjangoInstrumentor

        DjangoInstrumentor().instrument()


class FastapiInstrumentationActivator:
    instrumentation_name = "fastapi"

    def activate(self) -> None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor().instrument()


class PsycopgInstrumentationActivator:
    instrumentation_name = "psycopg"

    def activate(self) -> None:
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

        PsycopgInstrumentor().instrument(enable_commenter=True)


class SqlalchemyInstrumentationActivator:
    instrumentation_name = "sqlalchemy"

    def activate(self) -> None:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(enable_commenter=True)


class RedisInstrumentationActivator:
    instrumentation_name = "redis"

    def activate(self) -> None:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()


class ElasticsearchInstrumentationActivator:
    instrumentation_name = "elasticsearch"

    def activate(self) -> None:
        from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor

        ElasticsearchInstrumentor().instrument()
