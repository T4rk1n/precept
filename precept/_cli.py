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

from ._tools import is_windows
from ._logger import setup_logger


class AsyncWrapper:
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
        return await self.loop.run_in_executor(
            self.executor,
            functools.partial(fn, *args, **kwargs)
        )


def _flags_key(flags):
    return stringcase.snakecase(flags[-1].lstrip('-'))


class Argument(typing.NamedTuple):
    flags: typing.List[str]
    kwargs: dict


class CombinedFormatter(argparse.ArgumentDefaultsHelpFormatter,
                        argparse.RawDescriptionHelpFormatter):
    pass


class Command:
    arguments: typing.List[Argument]
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
            kw = dict(help='-', **arg.kwargs) \
                if 'default' in arg.kwargs and 'help' not in arg.kwargs \
                else arg.kwargs

            parser.add_argument(*arg.flags, **kw)

    @property
    def command_name(self):
        return self._command_name

    @command_name.setter
    def command_name(self, value):
        self._command_name = stringcase.spinalcase(value) if value else value


class Cli:
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
            self.parser.add_argument(
                *g.flags, **g.kwargs
            )

        self.commands = {
            x.__command__.command_name: x for x in commands
        }

        subparsers = self.parser.add_subparsers(
            title='Commands', dest='command'
        )

        for c in commands:
            c.__command__.register(subparsers)

    async def run(self, args=None):
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
            self.default_command(**vars(namespace))
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
    _commands = ()
    _prog_name = ''
    _global_arguments = []
    _default_configs: dict = {}
    _version = '0.0.1'

    def __init__(self, config_file=None, loop=None, executor=None):
        self._prog_name = self._prog_name or stringcase.spinalcase(
            self.__class__.__name__
        )
        self._configs = None

        if is_windows():
            colorama.init()

        self.logger = setup_logger(self._prog_name)
        self.async_wrapper = AsyncWrapper(loop, executor)

        self.cli = Cli(
            *(getattr(self, x) for x in self._commands),
            prog=self._prog_name,
            description=self.__doc__,
            config_file=config_file,
            global_arguments=[Argument(['-v', '--verbose'], {
                'action': 'store_true',
                'default': False
            })] + self._global_arguments,
            on_parse=self._on_parse,
            default_command=self.main
        )

    @property
    def configs(self):
        if self._configs:
            # Cached
            return self._configs
        if self.cli.config_file:
            configs = self._default_configs.copy()
            if os.path.exists(self.cli.config_file):
                with open(self.cli.config_file, 'r') as f:
                    configs = yaml.load(f, Loader=yaml.RoundTripLoader)
            else:
                os.makedirs(os.path.dirname(self.cli.config_file),
                            exist_ok=True)
                with open(self.cli.config_file, 'w') as f:
                    yaml.dump(configs, f, Dumper=yaml.RoundTripDumper)
            self._configs = configs
            return configs
        return {}

    def start(self):
        self.logger.info(f'{self._prog_name} {self._version}')
        self.async_wrapper.loop.run_until_complete(self.cli.run())

    def main(self, **kwargs):
        self.logger.error('Please enter a command')
        self.cli.parser.print_help()

    def _on_parse(self, args):
        if args.verbose:
            self.logger.setLevel(logging.DEBUG)

        if self.cli.config_file:
            self.logger.info(f'Using config {self.cli.config_file}')
