import itertools
import math
import pytest

from precept.console import print_table, spinner, progress_bar


@pytest.mark.async_test
async def test_spinner(capsys):
    messages = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight']

    namespace = {
        'i': 0,
    }

    def on_spin():
        _, err = capsys.readouterr()
        #
        if not err:
            # First one is always empty. (Possible bugs?)
            return False
        clean_err = err.strip()
        assert messages[namespace['i']] in clean_err
        namespace['i'] += 1

        return namespace['i'] >= len(messages)

    await spinner(
        on_spin,
        message=lambda: f'{messages[namespace["i"]]} ... '
    )
    assert namespace['i'] == len(messages)


@pytest.mark.async_test
@pytest.mark.parametrize(
    'max_value, dents',
    list(itertools.product(
        [50, 77.77, 88, 100, 200, 32422], [50, 20, 18, 99, 35, 80]
    ))
)
async def test_progress_bar(capsys, max_value, dents):
    max_value = 50

    namespace = {
        'i': 0,
    }

    def value_formatter(value, value_max):
        return f' {value/value_max * 100:.2f}%'

    def value_func():
        if namespace['i'] > 0:
            out, err = capsys.readouterr()
            clean = out.strip().split(']')[0].split('[')[-1]
            num = math.ceil(namespace['i'] / max_value * dents)
            assert num * '#' == clean[:num]
            assert clean[num:] == (dents - num) * '-'
        namespace['i'] += 1
        return namespace['i']

    await progress_bar(
        value_func,
        max_value=max_value,
        value_formatter=value_formatter,
        file=None,
        dents=dents,
    )


def test_table(capsys):
    table = [
        'one', 'two', 'three', 'four', 'five', 'six',
        'seven', 'eight', 'nine', 'ten', 'eleven'
    ]
    print_table(table)

    out, _ = capsys.readouterr()
    splitted = out.split('\n')
    for line in enumerate(splitted):
        assert len(line) < 79
