import sys

__all__ = [
    'is_windows',
]


def is_windows():
    return sys.platform == 'win32'
