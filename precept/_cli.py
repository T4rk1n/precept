"""Class based cli builder with sub commands."""
import argparse
import asyncio
import logging
import os
import typing
import functools

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import colorama
import stringcase
from ruamel import yaml

from ._immutable import ImmutableDict
from ._tools import is_windows
from ._logger import setup_logger


class AsyncExecutor:
    """Execute function a ThreadPool or ProcessPool."""
    def __init__(self, loop=None, executor=None):
        self.loop = loop or asyncio.get_event_loop()
        self.global_lock = asyncio.Lock(loop=loop)
        if executor:
            self.executor = executor
        elif is_windows():
            # Processes don't work good with windows.
            self.executor = ThreadPoolExecutor()
        else:
            self.executor = ProcessPoolExecutor()

    async def execute(self, fn, *args, **kwargs):
        """
        Execute a sync function asynchronously in the executor.

        :param fn: Synchronous function.
        :param args:
        :param kwargs:
        :return:
        """
        return await self.loop.run_in_executor(
            self.executor,
            functools.partial(fn, *args, **kwargs)
        )

    async def execute_with_lock(self, fn, *args, **kwargs):
        """
        Acquire lock before executing the function.

        :param fn: Synchronous function.
        :param args:
        :param kwargs:
        :return:
        """
        await self.global_lock.acquire()
        ret = await self.execute(fn, *args, **kwargs)
        self.global_lock.release()
        return ret


def _flags_key(flags):
    return stringcase.snakecase(flags[-1].lstrip('-'))


class Argument(ImmutableDict):
    """
    Argument of a Command, can either be optional or not depending on the flags
    """
    def __init__(
            self,
            *flags: str,
            type=None,
            help: str = None,
            choices: typing.Iterable = None,
            default: typing.Any = None,
            nargs: typing.Union[str, int] = None,
            action: str = None,
            required: bool = None,
            metavar: str = None,
            dest: str = None,
    ):
        super().__init__(**{
            k: v for k, v in locals().items()
            if k in self._prop_keys and v is not None
        })

    def register(self, parser):
        options = {k: v for k, v in self.items() if k != 'flags'}

        if 'default' in options and 'help' not in options:
            # Otherwise the default value don't show up.
            options['help'] = '-'

        parser.add_argument(*self.flags, **options)


class CombinedFormatter(argparse.ArgumentDefaultsHelpFormatter,
                        argparse.RawDescriptionHelpFormatter):
    pass


class Command:
    """
    Command decorator, methods of `CliApp` subclasses decorated with this gets
    a sub-command in the parser.

    Wrapped methods will gets the arguments by the ``Argument`` flag.
    """
    arguments: typing.Iterable[Argument]
    description: str

    def __init__(self, *arguments: Argument,
                 name=None, description=None, help=None):
        self.arguments = arguments
        self._command_name = None
        self.command_name = name
        self.description = description
        self.help = help

    def __call__(self, func):
        self.command_name = getattr(func, '__name__')

        setattr(func, '__command__', self)

        return func

    def register(self, subparsers):
        parser = subparsers.add_parser(
            self.command_name,
            description=self.description,
            help=self.help or self.description,
            formatter_class=CombinedFormatter
        )

        for arg in self.arguments:
            arg.register(parser)

    @property
    def command_name(self):
        return self._command_name

    @command_name.setter
    def command_name(self, value):
        self._command_name = stringcase.spinalcase(value) if value else value


class Cli:
    """argparse cli wrapper."""
    def __init__(self, *commands,
                 prog='',
                 description='',
                 formatter_class=CombinedFormatter,
                 config_file=None,
                 global_arguments=None,
                 default_command=None,
                 on_parse=None):
        self.prog = prog
        self.default_command = default_command
        self.parser = argparse.ArgumentParser(
            prog=self.prog,
            description=description,
            formatter_class=formatter_class,
        )
        self._config_file = config_file
        if config_file:
            self.parser.add_argument(
                '-c', '--config-file',
                default=config_file,
                help='Config file path'
            )

        self._global_arguments = global_arguments or []
        self.globals = {}
        self._on_parse = on_parse

        for g in self._global_arguments:
            g.register(self.parser)

        self.commands = {
            x.__command__.command_name: x for x in commands
        }

        subparsers = self.parser.add_subparsers(
            title='Commands', dest='command'
        )

        for c in commands:
            c.__command__.register(subparsers)

    async def run(self, args=None):
        """
        Parse and call the appropriate handler.

        :param args: None takes sys.argv
        :return:
        """
        namespace = self.parser.parse_args(args=args)
        command = self.commands.get(namespace.command)
        kw = vars(namespace).copy()
        kw.pop('command')

        if self._config_file:
            self._config_file = kw.pop('config_file')

        for g in self._global_arguments:
            key = stringcase.snakecase(g.flags[-1].lstrip('-'))
            self.globals[key] = kw.pop(key)

        if callable(self._on_parse):
            self._on_parse(namespace)

        if command:
            await command(**kw)
        elif self.default_command:
            await self.default_command(**vars(namespace))
        else:
            self.parser.print_help()

    @property
    def config_file(self):
        return self._config_file


class ConfigProp:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        g = instance.cli.globals.get(self.name)  # From cli arg priority.
        c = instance.configs.get(self.name)
        return g or c


class MetaCli(type):
    def __new__(mcs, name, bases, attributes):
        new_attributes = dict(**attributes)
        new_attributes['_commands'] = [
            x.__name__
            for x in attributes.values() if hasattr(x, '__command__')
        ]
        prog_name = attributes.get('_prog_name')
        new_attributes['_prog_name'] = prog_name or stringcase.spinalcase(name)

        default_configs = set(attributes.get('_default_configs', {}).keys())
        flags = [
            _flags_key(y.flags)
            for y in attributes.get('_global_arguments', [])
        ]

        for x in default_configs.union(flags):
            new_attributes[f'config_{x}'] = ConfigProp()

        return type.__new__(mcs, name, bases, new_attributes)


class CliApp(metaclass=MetaCli):
    """
    Auto cli generator, methods decorated with ``Command`` will have
    a corresponding sub-command in the cli application.

    Commands will get the arguments named as the last element of the command
    flags.

    Override `main` method for root handler, it gets all the `global_arguments`

    If a key is in both `global_arguments` and `configs`, it gets a property
    with key `config_{key}` that get the global first.
    """
    _commands = ()
    prog_name = ''
    global_arguments = []
    default_configs: dict = {}
    version = '0.0.1'

    def __init__(
            self,
            config_file=None,
            loop=None,
            executor=None,
            auto_write_configs=False,
            add_dump_config_command=False,
    ):
        """
        :param config_file: Path to the default config file to use. Can be
            specified with ``--config-file``
        :param loop: Asyncio loop to use.
        :param executor: concurrent executor to use.
        :param auto_write_configs: Automatically write the config file.
        :param add_dump_config_command: Add a ``dump-config`` command.
        """
        self.prog_name = self.prog_name or stringcase.spinalcase(
            self.__class__.__name__
        )
        self.auto_write_configs = auto_write_configs
        self._configs = None

        if is_windows():
            colorama.init()

        self.logger = setup_logger(self.prog_name)
        self.executor = AsyncExecutor(loop, executor)

        common_g_arguments = [
            Argument('-v', '--verbose', action='store_true', default=False),
            Argument('--log-file', type=argparse.FileType('w')),
            Argument('--quiet', action='store_true'),
        ]

        commands = [getattr(self, x) for x in self._commands]

        if add_dump_config_command:
            @Command(
                Argument(
                    '-o', '--outfile',
                    help='Write the current configs to this file.',
                    type=str,
                    default=config_file,
                ),
                name='dump-config',
                description='Dump the current configuration file content.'
            )
            async def dump_configs(outfile):
                os.makedirs(os.path.dirname(outfile), exist_ok=True)
                await self.executor.execute_with_lock(
                    self._write_configs, self.configs, outfile
                )
            commands.append(dump_configs)

        self.cli = Cli(
            *commands,
            prog=self.prog_name,
            description=str(self.__doc__),
            config_file=config_file,
            global_arguments=common_g_arguments + self.global_arguments,
            on_parse=self._on_parse,
            default_command=self.main
        )

    @property
    def configs(self):
        """
        Configs dictionary of the application, set ``config_file`` argument
        to use with the default configs.

        :return:
        """
        if self._configs:
            # Cached
            return self._configs
        if self.cli.config_file:
            configs = self.default_configs.copy()
            if os.path.exists(self.cli.config_file):
                with open(self.cli.config_file, 'r') as f:
                    configs = yaml.load(f, Loader=yaml.RoundTripLoader)
            else:
                if self.auto_write_configs:
                    os.makedirs(
                        os.path.dirname(self.cli.config_file),
                        exist_ok=True
                    )
                    self._write_configs(configs, self.cli.config_file)
            self._configs = ImmutableDict(**configs)
            return self._configs
        return {}

    def start(self):
        """
        Start the application loop.

        :return:
        """
        self.logger.info(f'{self.prog_name} {self.version}')
        self.executor.loop.run_until_complete(self.cli.run())

    async def main(self, **kwargs):
        """
        Handler when no command has been entered. Gets the globals arguments.

        :param kwargs: Global arguments.
        :return:
        """
        self.logger.error('Please enter a command')
        self.cli.parser.print_help()

    def _on_parse(self, args):
        if args.verbose:
            self.logger.setLevel(logging.DEBUG)

        if args.log_file:
            self.logger.addHandler(logging.StreamHandler(args.log_file))

        if args.quiet:
            self.logger.setLevel(logging.ERROR)

        if self.cli.config_file:
            self.logger.info(f'Using config {self.cli.config_file}')

    # noinspection PyMethodMayBeStatic
    def _write_configs(self, configs, file):
        with open(file, 'w') as f:
            yaml.dump(dict(configs), f, Dumper=yaml.RoundTripDumper)
