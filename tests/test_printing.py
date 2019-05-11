import pytest

from precept import spinner


@pytest.mark.async_test
async def test_spinner(capsys):
    messages = ['one', 'two', 'three', 'four', 'five', 'six']

    namespace = {
        'i': 0
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
