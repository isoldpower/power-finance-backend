from datetime import timedelta
from functools import cache

from django.conf import settings
from redis.asyncio import Redis

from data_write_core.domain.exceptions import DemoSessionsDisabledError

from .hmac_demo_visit_codec import HmacDemoVisitCodec
from .jwt_demo_token_issuer import JwtDemoTokenIssuer
from .redis_demo_visit_registry import RedisDemoVisitRegistry


def build_visit_codec() -> HmacDemoVisitCodec:
    demo_settings = settings.DEMO_SESSIONS
    if not demo_settings["VISIT_SECRET"]:
        raise DemoSessionsDisabledError()

    return HmacDemoVisitCodec(
        secret=demo_settings["VISIT_SECRET"],
        lifetime=timedelta(seconds=demo_settings["VISIT_TTL_SECONDS"]),
    )


def build_visit_registry() -> RedisDemoVisitRegistry:
    redis_settings = settings.REDIS
    demo_settings = settings.DEMO_SESSIONS

    return RedisDemoVisitRegistry(
        redis=_demo_visit_redis(
            redis_settings["HOST"],
            int(redis_settings["PORT"]),
            redis_settings["PASSWORD"],
            int(demo_settings["VISIT_REDIS_DB"]),
        ),
        client_key_secret=demo_settings["VISIT_SECRET"],
    )


def build_token_issuer() -> JwtDemoTokenIssuer:
    demo_settings = settings.DEMO_SESSIONS
    if not demo_settings["TOKEN_SECRET"]:
        raise DemoSessionsDisabledError()

    return JwtDemoTokenIssuer(
        secret=demo_settings["TOKEN_SECRET"],
        issuer=demo_settings["TOKEN_ISSUER"],
        lifetime=timedelta(seconds=demo_settings["TOKEN_TTL_SECONDS"]),
    )


def visit_rotation_window() -> timedelta:
    return timedelta(seconds=settings.DEMO_SESSIONS["VISIT_ROTATION_SECONDS"])


@cache
def _demo_visit_redis(host: str, port: int, password: str, database: int) -> Redis:
    return Redis(host=host, port=port, password=password or None, db=database)
