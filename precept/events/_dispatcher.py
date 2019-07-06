import collections

from ._event import Event


class EventDispatcher:
    """Dispatch events to subscribers functions."""
    def __init__(self):
        self._subscribers = collections.defaultdict(list)

    def subscribe(self, event: str, func):
        """
        Subscribe func to execute every time event is dispatched.

        :param event: The event to subscribe to.
        :param func: The func to call when event is dispathed.
        :return:
        """
        self._subscribers[event].append(func)

    async def dispatch(self, event: str, **payload):
        """
        Dispatch an event with optional payload data.

        :param event: Name of the event.
        :param payload: Data of the event.
        :return:
        """
        action = Event(event, payload=payload)
        for subscriber in self._subscribers[event]:
            await subscriber(action)
            if action.stop:
                break
            action.num += 1
