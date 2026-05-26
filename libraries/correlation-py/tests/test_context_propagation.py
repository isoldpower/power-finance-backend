"""ContextVar propagation across asyncio.Task and thread boundaries.

The whole point of using ContextVar (over thread-local or a global) is
that spawned asyncio Tasks inherit the parent context. Pin both halves
of that contract:
- a Task created while a correlation id is set sees that id;
- a Task that mutates the id with attach/reset only affects itself,
  not the parent (Tasks snapshot the parent context on creation).

Also pin that ContextVars are isolated across threads — important
because Django's sync middleware path runs in worker threads under ASGI.
"""

from __future__ import annotations

import asyncio
import threading
import unittest

from correlation.utilities.context import (
    attach_correlation_id,
    get_correlation_id,
    reset_correlation_id,
)


class AsyncioTaskPropagationTests(unittest.IsolatedAsyncioTestCase):
    async def test_spawned_task_inherits_parent_correlation_id(self) -> None:
        token = attach_correlation_id("parent-cid")
        try:
            captured: dict[str, str | None] = {}

            async def child() -> None:
                captured["seen"] = get_correlation_id()

            await asyncio.create_task(child())

            self.assertEqual(captured["seen"], "parent-cid")
        finally:
            reset_correlation_id(token)

    async def test_child_task_mutation_does_not_leak_to_parent(self) -> None:
        # Tasks snapshot the parent's Context on creation; changes inside
        # the Task affect that snapshot only.
        parent_token = attach_correlation_id("parent")
        try:

            async def child_mutates() -> None:
                child_token = attach_correlation_id("child")
                try:
                    # noop — exists just to mutate
                    pass
                finally:
                    reset_correlation_id(child_token)

            await asyncio.create_task(child_mutates())

            self.assertEqual(get_correlation_id(), "parent")
        finally:
            reset_correlation_id(parent_token)

    async def test_concurrent_tasks_do_not_observe_each_others_ids(self) -> None:
        # Two tasks each set their own id and yield to the loop. Neither
        # must observe the other's id when it resumes.
        async def one_request(label: str) -> str | None:
            token = attach_correlation_id(label)
            try:
                # Yield to give the other task a chance to interleave.
                await asyncio.sleep(0)
                return get_correlation_id()
            finally:
                reset_correlation_id(token)

        a_seen, b_seen = await asyncio.gather(
            one_request("A"),
            one_request("B"),
        )

        self.assertEqual(a_seen, "A")
        self.assertEqual(b_seen, "B")


class ThreadIsolationTests(unittest.TestCase):
    def test_correlation_id_set_in_main_is_not_seen_by_a_new_thread(self) -> None:
        # ContextVars default-isolate across raw threads (no copy_context).
        # If this ever changes, sync middleware running on worker threads
        # could start cross-contaminating requests.
        token = attach_correlation_id("main-thread")
        try:
            observed: dict[str, str | None] = {}

            def in_thread() -> None:
                observed["seen"] = get_correlation_id()

            thread = threading.Thread(target=in_thread)
            thread.start()
            thread.join()

            self.assertIsNone(observed["seen"])
        finally:
            reset_correlation_id(token)
