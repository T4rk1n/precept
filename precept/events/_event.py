import enum
import time


from .._tools import AutoNameEnum
from .._immutable import ImmutableDict


class Event:
    """
    Event with payload and stop property.
    """
    def __init__(self, name: str, payload: dict):
        self.name = name
        self.stop: bool = False
        self.num = 0
        self.payload = ImmutableDict(**payload)
        self.timestamp = time.time()

    def __str__(self):  # pragma: no cover
        return self.name

    def __repr__(self):  # pragma: no cover
        return f'<{self.__class__.__name__} {self.name} {self.timestamp}>'


class PreceptEvent(AutoNameEnum):
    """Precept cli events."""
    BEFORE_CLI_START = enum.auto()
    CLI_PARSED = enum.auto()
    CLI_STARTED = enum.auto()
    CLI_STOPPED = enum.auto()

    # pylint: disable=comparison-with-callable
    def __eq__(self, other):  # pragma: no cover
        if isinstance(other, PreceptEvent):
            return self.value == other.value
        if isinstance(other, str):
            return other in (self.value, self.name, str(self))
        if isinstance(other, Event):
            return other.name == self.value
        return False

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        # pylint: disable=invalid-str-returned
        return self.value
