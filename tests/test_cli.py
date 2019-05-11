import os
import sys

import pytest

from precept import Precept, Command, Argument


class SimpleCli(Precept):
    result = None
    global_arguments = [
        Argument('--universal'),
    ]

    async def main(self, **kwargs):
        self.result = kwargs.get('universal')

    @Command(
        Argument(
            'foo',
            type=int,
        ),
        Argument(
            '--bar',
            default=3,
            type=int,
        )
    )
    async def simple(self, foo, bar):
        """Help from docstring"""
        self.result = foo + bar

    @Command(
        Argument('message'),
        Argument('--debug', action='store_true')
    )
    async def log_result(self, message, debug):
        if debug:
            self.logger.debug(message)
        else:
            self.logger.info(message)


def test_simple_cli():
    cli = SimpleCli()
    cli.start('--quiet simple 1'.split(' '))

    assert cli.result == 4

    cli.start('--quiet simple 3 --bar 6'.split(' '))
    assert cli.result == 9


def test_main():
    cli = SimpleCli()
    cli.start('--quiet --universal foo'.split(' '))

    assert cli.result == 'foo'


@pytest.mark.parametrize(
    'debug, verbose',
    [
        (False, False),
        (True, False),
        (False, True),
        (True, True)
    ]
)
def test_log_file(debug, verbose):
    log_file = './.logs'
    message = "Foo bar should be in there."
    try:
        cli = SimpleCli()
        arguments = f'--log-file {log_file} log-result'.split(' ')
        arguments.append(f'"{message}"')

        if verbose:
            arguments.insert(0, '-v')
        if debug:
            arguments.append('--debug')

        cli.start(arguments)

        with open(log_file, 'r') as f:
            logs = f.read()

        if debug and not verbose:
            assert message not in logs
        else:
            assert message in logs
    finally:
        if os.path.exists(log_file):
            os.remove(log_file)


def test_command_docstring(capsys, monkeypatch):
    cli = SimpleCli()

    def patch_exit(_):
        # Need to patch exit because calling help will exit from argparse
        # The command will be executed...
        pass

    monkeypatch.setattr(sys, 'exit', patch_exit)

    cli.start('--help'.split(' '))

    out, _ = capsys.readouterr()
    assert 'Help from docstring' in out
