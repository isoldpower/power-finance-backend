from collections import defaultdict
from queue import Queue
from typing import DefaultDict

from finances.application.interfaces import NotificationBroker


class InMemoryNotificationBroker(NotificationBroker):
    def __init__(self) -> None:
        self._subscriptions: DefaultDict[int, list[Queue]] = defaultdict(list)

    def subscribe(self, user_id: int) -> Queue:
        queue = Queue()

        if not user_id in self._subscriptions:
            self._subscriptions[user_id] = [queue]
        else:
            self._subscriptions[user_id].append(queue)

        return queue

    def unsubscribe(self, user_id: int, queue: Queue) -> None:
        queues = self._subscriptions.get(user_id, [])
        if queue in queues:
            queues.remove(queue)

        if not queues and user_id in self._subscriptions:
            del self._subscriptions[user_id]

    def publish(self, user_id: int, payload: dict) -> None:
        queues = self._subscriptions.get(user_id, [])
        for queue in queues:
            queue.put(payload)