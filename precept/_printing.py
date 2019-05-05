import asyncio
import sys

from colorama import Style, Fore

__all__ = [
    'colorize',
    'spinner'
]


def colorize(text, bg=None, fg=None, style=None):
    fg = fg or ''
    bg = bg or ''
    style = style or ''
    return f'{bg}{fg}{style}{text}{Style.RESET_ALL}'


async def spinner(condition,
                  sleep_time=0.25, message='',
                  fg=Fore.WHITE, bg=None):  # pragma: no cover
    i = 0
    while not condition():
        m = i % 8
        i += 1
        p = ''
        if m == 0:
            p = '|'
        elif m == 1:
            p = '/'
        elif m == 2:
            p = '-'
        elif m == 3:
            p = '\\'
        elif m == 4:
            p = '|'
        elif m == 5:
            p = '/'
        elif m == 6:
            p = '-'
        elif m == 7:
            p = '\\'
        if callable(message):
            msg = message()
        else:
            msg = message
        m = colorize(f'{msg} {p}', fg=fg, bg=bg)
        msg = f'\r\x1b[K{m}'
        print(msg, end='', flush=True, file=sys.stderr)
        await asyncio.sleep(sleep_time)
