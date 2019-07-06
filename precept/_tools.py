import sys
from enum import Enum

__all__ = [
    'is_windows',
    'AutoNameEnum'
]


def is_windows():
    return sys.platform == 'win32'


class AutoNameEnum(Enum):
    # noinspection PyMethodParameters
    # pylint: disable=no-self-argument, unused-argument, no-member
    def _generate_next_value_(name, *args):
        return name.lower()
