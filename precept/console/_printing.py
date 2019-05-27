import asyncio
import sys

from colorama import Style, Fore

__all__ = [
    'colorize',
    'spinner',
    'format_table',
    'print_table',
    'goto_xy',
]


def colorize(text, bg=None, fg=None, style=None):
    fg = fg or ''
    bg = bg or ''
    style = style or ''
    return f'{bg}{fg}{style}{text}{Style.RESET_ALL}'


async def spinner(condition,
                  sleep_time=0.25, message='',
                  fg=Fore.WHITE, bg=None):
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
        else:  # pragma: no cover
            msg = message
        m = colorize(f'{msg} {p}', fg=fg, bg=bg)
        msg = f'\r\x1b[K{m}'
        print(msg, end='', flush=True, file=sys.stderr)
        await asyncio.sleep(sleep_time)


def chunk_list(data, n):
    for i in range(0, len(data), n):
        yield data[i:i+n]


def format_table(data, formatting=None):
    # 2 padding + '|'
    max_len = max(len(x) for x in data) + 3
    if max_len % 2 == 0:  # pragma: no cover
        # Revert uneven for a bit nicer look.
        max_len += 1
    min_len = len(data) * max_len
    r = 79 / max_len

    if r - int(r) > 0:
        col = int(r) - 1
    else:  # pragma: no cover
        col = int(r)

    if min_len < 79:  # pragma: no cover
        row_len = min_len + len(data) + 1
    else:
        row_len = max_len * col
        # Add the columns + 1 for the first '|'
        row_len += col + 1

    if not formatting:
        formatting = lambda e: e  # noqa: E731

    chunks = chunk_list(data, col)
    rows = ['-' * row_len]
    for chunk in chunks:
        rows.append(
            '|{}|'.format(
                '|'.join(
                    formatting(c.center(max_len))
                    for c in chunk
                )
            )
        )
        rows.append('-' * row_len)
    return rows


def print_table(data, formatting=None, file=sys.stdout):
    print('\n'.join(format_table(data, formatting,)), file=file)


def goto_xy(stream, x, y):  # pragma: no cover
    # Make sure colorama is init on windows.
    print('%c[%d;%df' % (0x1B, y, x), end='', file=stream)
