import contextlib
import time

from aiokafka.admin import AIOKafkaAdminClient

from ..logger_shortcuts import warn_sandbox_registry_unreachable
from ..sandbox_group_id import resolve_sandbox_scoped_group_id

REFRESH_SECONDS = 10.0


class KafkaSandboxGroupRegistry:
    """Answers "is some sandbox running its own consumer for my service?".

    The answer is already in Kafka: a sandbox consumer runs under a group id derived
    from the baseline's, so the baseline can name the group its counterpart would use
    and ask whether it exists. Nothing registers, nothing heartbeats, and nothing has
    to be cleaned up — the group appears on that consumer's first run and Kafka drops
    it when its committed offsets expire.

    Using existence rather than liveness is deliberate. A stopped consumer leaves its
    group behind with committed offsets, so the claim survives a restart and its owner
    resumes from its own offset. A liveness check would hand those events to the
    baseline instead, and the sandbox would then apply them a second time.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        own_group_id: str,
        *,
        refresh_seconds: float = REFRESH_SECONDS,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._own_group_id = own_group_id
        self._refresh_seconds = refresh_seconds
        self._group_ids: frozenset[str] = frozenset()
        self._read_at: float | None = None

    async def has_consumer_for(self, sandbox_id: str) -> bool:
        candidate = resolve_sandbox_scoped_group_id(self._own_group_id, sandbox_id)

        return candidate in await self._known_group_ids()

    async def _known_group_ids(self) -> frozenset[str]:
        if self._read_at is not None and time.monotonic() - self._read_at < self._refresh_seconds:
            return self._group_ids

        admin_client = AIOKafkaAdminClient(bootstrap_servers=self._bootstrap_servers)
        try:
            await admin_client.start()
            listed = await admin_client.list_consumer_groups()
            self._group_ids = frozenset(str(entry[0]) for entry in listed)
            self._read_at = time.monotonic()
        except Exception as error:
            # Leave the previous answer in place and try again on the next message
            # rather than caching a lie. A first failure means no sandbox is known,
            # which the policy reads as "claimed" — a gap, never a double-apply.
            warn_sandbox_registry_unreachable(error)
        finally:
            with contextlib.suppress(Exception):
                await admin_client.close()

        return self._group_ids

    @property
    def was_read(self) -> bool:
        return self._read_at is not None
