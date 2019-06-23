import logging
import sys

from colorama import Fore, Style

from .console import colorize

_colors = {
    'INFO': {
        'fg': Fore.LIGHTBLUE_EX,
        'style': Style.BRIGHT,
    },
    'DEBUG': {
        'fg': Fore.LIGHTBLACK_EX,
        'style': Style.BRIGHT,
    },
    'ERROR': {
        'fg': Fore.RED,
        'style': Style.BRIGHT,
    },
    'WARNING': {
        'fg': Fore.YELLOW,
        'style': Style.BRIGHT,
    },
}


class ColorFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, colors=None, style='%'):
        super(ColorFormatter, self).__init__(
            fmt=fmt, datefmt=datefmt, style=style
        )
        self.colors = colors or _colors

    def format(self, record: logging.LogRecord):
        formatted = super(ColorFormatter, self).format(record)
        return colorize(
            f'\r\x1b[K{formatted}',
            **self.colors.get(record.levelname)
        )


def setup_logger(
        logger_name,
        level=logging.INFO,
        fmt=None,
        datefmt=None,
        stream=sys.stderr,
        colors=None,
        style='%',
):
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        std_handler = logging.StreamHandler(stream=stream)
        std_handler.setFormatter(ColorFormatter(fmt, datefmt, colors, style))
        logger.addHandler(std_handler)
    logger.setLevel(level)
    logger.propagate = False

    return logger
