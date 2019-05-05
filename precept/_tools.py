import sys

__all__ = [
    'chunk_list',
    'is_windows',
    'format_table',
    'print_table',
    'goto_xy',
]


def chunk_list(data, n):
    for i in range(0, len(data), n):
        yield data[i:i+n]


def is_windows():
    return sys.platform == 'win32'


def format_table(data, formatting=None):
    # 2 padding + '|'
    max_len = max(len(x) for x in data) + 3
    if max_len % 2 == 0:
        # Revert uneven for a bit nicer look.
        max_len += 1
    min_len = len(data) * max_len
    r = 79 / max_len

    if r - int(r) > 0:
        col = int(r) - 1
    else:
        col = int(r)

    if min_len < 79:
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


def print_table(data, formatting=None, file=sys.stdout):  # pragma: no cover
    print('\n'.join(format_table(data, formatting,)), file=file)


def goto_xy(stream, x, y):  # pragma: no cover
    # Make sure colorama is init on windows.
    print('%c[%d;%df' % (0x1B, y, x), end='', file=stream)
