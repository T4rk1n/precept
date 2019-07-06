import argparse
import itertools
import logging
import os
import sys
import typing

import colorama
import stringcase

from .events import EventDispatcher, PreceptEvent
from ._configs import Config, config_factory
from ._tools import is_windows
from ._cli import CombinedFormatter, Cli, Argument, Command
from ._executor import AsyncExecutor
from ._logger import setup_logger

from ._cli import CommandMeta


class PreceptMeta(CommandMeta):
    def __new__(mcs, name, bases, attributes):
        new_attributes = dict(**attributes)
        prog_name = attributes.get('_prog_name')
        new_attributes['_prog_name'] = prog_name or stringcase.spinalcase(name)
        # pylint: disable=too-many-function-args
        return CommandMeta.__new__(mcs, name, bases, new_attributes)


class Precept(metaclass=PreceptMeta):
    """
    Auto cli generator, methods decorated with ``Command`` will have
    a corresponding sub-command in the cli application.

    Commands will get the arguments named as the last element of the command
    flags.

    Override `main` method for root handler, it gets all the `global_arguments`

    If a key is in both `global_arguments` and `configs`, it gets a property
    with key `config_{key}` that get the global first.
    """
    _commands = []
    prog_name = ''
    global_arguments = []
    default_configs: dict = {}
    version = '0.0.1'
    config_class = None
    config: Config = None

    # pylint: disable=too-many-locals
    def __init__(
            self,
            config_file: typing.Union[str, typing.List[str]] = None,
            loop=None,
            executor=None,
            executor_max_workers=None,
            add_dump_config_command=False,
            help_formatter=CombinedFormatter,
            logger_level=logging.INFO,
            logger_fmt=None,
            logger_datefmt=None,
            logger_stream=sys.stderr,
            logger_colors=None,
            logger_style='%',
    ):
        """
        :param config_file: Path to the default config file to use. Can be
            specified with ``--config-file``
        :param loop: Asyncio loop to use.
        :param executor: concurrent executor to use.
        :param add_dump_config_command: Add a ``dump-config`` command.
        """
        self.prog_name = self.prog_name or stringcase.spinalcase(
            self.__class__.__name__
        )
        self._config_file = config_file
        if not isinstance(self._config_file, list)\
                and isinstance(config_file, str):
            self._config_file = [config_file]
        self._user_configs = None

        if is_windows():  # pragma: no cover
            colorama.init()

        self.logger = setup_logger(
            self.prog_name,
            logger_level,
            logger_fmt,
            logger_datefmt,
            logger_stream,
            logger_colors,
            style=logger_style
        )
        self.executor = AsyncExecutor(
            loop, executor, max_workers=executor_max_workers
        )
        self.loop = self.executor.loop
        self.events = EventDispatcher()

        common_g_arguments = [
            Argument('-v', '--verbose', action='store_true', default=False),
            Argument('--log-file', type=argparse.FileType('w')),
            Argument('--quiet', action='store_true'),
        ]

        if config_file:
            common_g_arguments.append(
                Argument(
                    '-c', '--config-file',
                    type=str,
                    help='Config file path'
                )
            )

        if self.config is None:
            if self.config_class and self.config:
                # pylint: disable=not-callable
                self.config: Config = self.config_class()
            elif self.default_configs:
                cls = config_factory(self.default_configs)
                self.config = cls()
            else:
                self.config = Config()

        # Insert global arguments from config
        for _, _, prop in self.config.get_prop_paths():
            if prop.auto_global:
                key = f'--{stringcase.spinalcase(prop.qualified_name)}'
                common_g_arguments.append(
                    Argument(
                        key,
                        type=prop.config_type,
                        default=prop.default,
                        help=prop.comment,
                    )
                )

        # Gather commands
        attributes = dir(self)
        commands = list(
            itertools.chain(*(
                # Don't go into descriptors yet, class members gets the
                getattr(self.__class__, x).get_commands()
                for x in self._commands if x in attributes
            ))
        )

        if add_dump_config_command:
            @Command(
                Argument(
                    'outfile',
                    help='Write the current configs to this file.',
                    type=str,
                    default=config_file,
                ),
                description='Dump the current configuration file content.'
            )
            async def dump_configs(outfile):
                dirname = os.path.dirname(outfile)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)
                self.config.save(outfile)

            commands.append((
                dump_configs.command.command_name,
                dump_configs.command,
                dump_configs
            ))

        self.cli = Cli(
            *[
                (
                    x[0],
                    x[1],
                    # Now go into the descriptors for that self argument.
                    getattr(self, x[1].obj_name)
                    if x[1].obj_name in attributes else x[2]
                ) for x in commands
            ],
            prog=self.prog_name,
            description=getattr(self, '__doc__', ''),
            global_arguments=common_g_arguments + self.global_arguments,
            on_parse=self._on_parse,
            default_command=self.main,
            formatter_class=help_formatter,
            events=self.events
        )

        setattr(self.config, '_app', self)

    @property
    def config_path(self):
        if self._user_configs:
            return self._user_configs
        for config in self._config_file:
            if os.path.exists(config):
                return config
        return ''

    def start(self, args=None):
        """
        Start the application loop.

        :return:
        """
        self.loop.run_until_complete(
            self.events.dispatch(str(PreceptEvent.BEFORE_CLI_START))
        )
        self.loop.run_until_complete(self.cli.run(args=args))
        self.loop.run_until_complete(
            self.events.dispatch(str(PreceptEvent.CLI_STOPPED))
        )

    # pylint: disable=unused-argument
    async def main(self, **kwargs):
        """
        Handler when no command has been entered. Gets the globals arguments.

        :param kwargs: Global arguments.
        :return:
        """
        self.logger.error('Please enter a command')
        self.cli.parser.print_help()

    async def _on_parse(self, args):
        if args.verbose:
            self.logger.setLevel(logging.DEBUG)

        if args.log_file:
            self.logger.addHandler(logging.StreamHandler(args.log_file))

        if args.quiet:
            self.logger.setLevel(logging.ERROR)

        if self._config_file:
            if args.config_file:
                self._user_configs = args.config_file

            if self.config_path:
                self.logger.info(f'Using config {self.config_path}')
                self.config.read_file(self.config_path)

        await self.events.dispatch(
            str(PreceptEvent.CLI_PARSED),
            arguments=args
        )

        self.logger.info(f'{self.prog_name} {self.version}')
