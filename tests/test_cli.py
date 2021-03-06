import os
import sys

import pytest

from precept import Precept, Command, Argument
from precept.events import PreceptEvent


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

    @Command(
        Argument('--nested')
    )
    class Nested:
        nested = None
        plain_result = None
        nest_much = None

        @Command(
            Argument('much')
        )
        async def nest(self, much):
            self.nest_much = f'{self.nested}-{much}'

        @Command()
        async def plain(self):
            self.plain_result = 'plain foo'

    # pylint: disable=unused-argument
    @Command(
        auto=True
    )
    async def autoarg(
            self,
            required: str,
            keyword: str = 'default_value',
            number: int = 22
    ):
        self.result = locals()


def test_simple_cli():
    cli = SimpleCli()
    cli.start('--quiet simple 1')

    assert cli.result == 4

    cli.start('--quiet simple 3 --bar 6')
    assert cli.result == 9


def test_main():
    cli = SimpleCli()
    cli.start('--quiet --universal foo')

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

    cli.start('--help')

    out, _ = capsys.readouterr()
    assert 'Help from docstring' in out
    # Bug if Precept has no docstring it print None instead of nothing.
    assert 'None' not in out


def test_nested_command():
    cli = SimpleCli()

    cli.start('nested --nested=foo nest bar')

    assert cli.Nested.nest_much == 'foo-bar'

    cli.start('nested plain')

    assert cli.Nested.plain_result == 'plain foo'


def test_auto_arguments():
    cli = SimpleCli()

    cli.start('autoarg bar')

    assert cli.result['required'] == 'bar'
    assert cli.result['keyword'] == 'default_value'
    assert cli.result['number'] == 22

    cli.start('autoarg foo --keyword=bar --number=99')

    assert cli.result['required'] == 'foo'
    assert cli.result['keyword'] == 'bar'
    assert cli.result['number'] == 99


def test_commands_subclasses():
    # test that subclasses inherit all parent commands + new ones.
    class SubCli(SimpleCli):
        @Command()
        async def new_command(self):
            self.result = 'new'

    cli = SubCli()
    assert len(cli.cli.commands) == 7
    cli.start('--quiet simple 3 --bar 6')
    assert cli.result == 9
    cli.start('new-command')
    assert cli.result == 'new'


def test_events():

    events = []
    commands = []

    async def on_event(event):
        events.append(event.name)

        if event == PreceptEvent.CLI_STARTED:
            commands.append(event.payload.command)

    cli = SimpleCli()
    for pre_event in PreceptEvent:
        cli.events.subscribe(pre_event, on_event)

    cli.start('simple 3')

    assert len(events) == 4
    assert commands[0] == 'simple'

    for act in PreceptEvent:
        assert act in events
