from dataclasses import dataclass

from django.conf import settings

DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_BATCH_LIMIT = 200


@dataclass(frozen=True)
class ActionExpirySettings:
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    batch_limit: int = DEFAULT_BATCH_LIMIT


def get_action_expiry_settings() -> ActionExpirySettings:
    configured = getattr(settings, "ACTION_EXPIRY", {})

    return ActionExpirySettings(
        interval_seconds=int(
            configured.get(
                "INTERVAL_SECONDS",
                DEFAULT_INTERVAL_SECONDS,
            )
        ),
        batch_limit=int(
            configured.get(
                "BATCH_LIMIT",
                DEFAULT_BATCH_LIMIT,
            )
        ),
    )
