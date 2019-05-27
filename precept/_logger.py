import datetime
import logging
import sys

from colorama import Back, Fore, Style

from .console import colorize

_colors = {
    'levels': {
        'INFO': {
            'fg': Fore.BLACK,
            'bg': Back.BLUE,
            'style': Style.BRIGHT,
        },
        'DEBUG': {
            'fg': Fore.BLACK,
            'bg': Back.RED,
            'style': Style.BRIGHT,
        },
        'ERROR': {
            'fg': Fore.BLACK,
            'bg': Back.RED,
            'style': Style.BRIGHT,
        },
        'WARNING': {
            'fg': Fore.BLACK,
            'bg': Back.RED,
            'style': Style.BRIGHT,
        },
    },
    'msg': {
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
    },
    'created': {},
    'logger_name': {}
}


class ColorFormatter(logging.Formatter):
    """
    fmt takes in the following keys:

    - `{msg}`
    - `{level}`
    - `{created}`
    - `{logger_name}`
    """
    def __init__(self, fmt='{msg}', datefmt='%H:%M:%S', colors=None):
        super(ColorFormatter, self).__init__(datefmt=datefmt)
        self.fmt = fmt
        self.colors = colors or _colors

    def format(self, record: logging.LogRecord):
        level_colors = self.colors.get('levels', {})
        level = level_colors.get(record.levelname,
                                 level_colors.get('ERROR'))

        level = colorize(f' {record.levelname}'.ljust(11), **level)
        msg = record.getMessage()
        ts = datetime.datetime.fromtimestamp(record.created).strftime(
            self.datefmt
        )

        return self.fmt.format(
            msg=colorize(f'\r\x1b[K{msg}',
                         **self.colors.get('msg').get(record.levelname)),
            level=level,
            created=ts
        )


def setup_logger(logger_name,
                 level=logging.INFO,
                 fmt='{msg}',
                 datefmt='%H:%M:%S',
                 stream=sys.stderr,
                 colors=None):
    logger = logging.getLogger(logger_name)
    std_handler = logging.StreamHandler(stream=stream)
    std_handler.setFormatter(ColorFormatter(fmt, datefmt, colors))
    logger.addHandler(std_handler)
    logger.setLevel(level)
    logger.propagate = False

    return logger
