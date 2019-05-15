"""Class based cli builder with sub commands."""
import argparse
import asyncio
import itertools
import logging
import os
import typing
import functools

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import colorama
import stringcase

from ._configs import Config, config_factory
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
        elif is_windows():  # pragma: no cover
            # Processes don't work good with windows.
            self.executor = ThreadPoolExecutor()
        else:  # pragma: no cover
            self.executor = ProcessPoolExecutor()

    async def execute(self, func, *args, **kwargs):
        """
        Execute a sync function asynchronously in the executor.

        :param func: Synchronous function.
        :param args:
        :param kwargs:
        :return:
        """
        return await self.loop.run_in_executor(
            self.executor,
            functools.partial(func, *args, **kwargs)
        )

    # pragma: no cover
    async def execute_with_lock(self, func, *args, **kwargs):
        """
        Acquire lock before executing the function.

        :param func: Synchronous function.
        :param args:
        :param kwargs:
        :return:
        """
        await self.global_lock.acquire()
        ret = await self.execute(func, *args, **kwargs)
        self.global_lock.release()
        return ret


def _flags_key(flags):
    return stringcase.snakecase(flags[-1].lstrip('-'))


class Argument(ImmutableDict):
    """
    Argument of a Command, can either be optional or not depending on the flags
    """

    # pylint: disable=unused-argument, redefined-builtin
    def __init__(
            self,
            *flags: str,
            type: type = None,
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

        flags = self.flags
        if len(self.flags) == 1 and not self.flags[0].startswith('-'):
            flags = [stringcase.snakecase(flags[0])]

        parser.add_argument(*flags, **options)

    @property
    def flag_key(self):
        return _flags_key(self.flags)


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

    # pylint: disable=redefined-builtin
    def __init__(self, *arguments: Argument,
                 name=None, description=None, help=None):
        self.arguments = arguments
        self._command_name = None
        self.command_name = name
        self.description = description
        self.help = help
        self._wrapped = None
        self.obj_name = None

    def __call__(self, obj):
        self.obj_name = getattr(obj, '__name__')
        if not self.command_name:
            self.command_name = self.obj_name

        if not self.description:
            self.description = getattr(obj, '__doc__', '')

        if isinstance(obj, type):

            # pylint: disable=used-before-assignment
            class NewCommand(obj, CommandClass, metaclass=CommandMeta):
                command = self

            self._wrapped = NewCommand()
        else:
            self._wrapped = CommandFunction(obj, self)

        return self._wrapped

    def register(self, subparsers):
        parser = subparsers.add_parser(
            self.command_name,
            description=self.description,
            help=self.help or self.description,
            formatter_class=CombinedFormatter
        )
        if isinstance(self._wrapped, CommandClass):
            subs = parser.add_subparsers(
                title='Commands', dest='command'
            )
            # noinspection PyProtectedMember
            for command_name, command, _ in self._wrapped.get_commands():
                # get_commands return itself so make sure it's not the same.
                if command_name != self.command_name:
                    command.register(subs)
        for arg in self.arguments:
            arg.register(parser)

    @property
    def command_name(self):
        return self._command_name

    @command_name.setter
    def command_name(self, value):
        self._command_name = stringcase.spinalcase(value) if value else value

    def __hash__(self):
        return self.command_name


class WrappedCommand:
    command: Command

    def __repr__(self):  # pragma: no cover
        return f'<{self.__class__.__name__} "{self.command.command_name}">'

    def get_commands(self) -> typing.Tuple[str, Command, typing.Callable]:
        raise NotImplementedError


class CommandFunction(WrappedCommand):
    def __init__(self, func, command):
        self.command = command
        self.func = functools.wraps(self)(func)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __get__(self, instance, owner):
        # Allow to use the self of the class
        if instance is None:
            return self
        return functools.partial(self.__call__, instance)

    def get_commands(self):
        return [(self.command.command_name, self.command, self)]

    def set_func(self, func):
        self.func = func


class CommandClass(WrappedCommand):
    _commands: typing.List[str]

    def __call__(self, command, *args, **kwargs):
        return getattr(self, command)(*args, **kwargs)

    def get_commands(self):
        c = []
        for command in (getattr(self.__class__, x) for x in self._commands):
            if issubclass(command.__class__, CommandClass):
                # Recursively get all the commands.
                c += command.get_commands()
            else:
                # Get the true one.
                c.append((
                    command.command.command_name,
                    command.command,
                    self.clean_arguments(
                        getattr(self, command.command.obj_name))
                ))

        # noinspection PyTypeChecker
        return c + [(self.command.command_name, self.command, self)]

    def clean_arguments(self, func):

        @functools.wraps(func)
        def wrap_arguments(*args, **kwargs):
            to_clean = []

            for argument in self.command.arguments:
                key = argument.flag_key
                value = kwargs.get(key)
                setattr(self, key, value)
                to_clean.append(key)

            cleaned = {k: v for k, v in kwargs.items() if k not in to_clean}
            return func(*args, **cleaned)

        return wrap_arguments


class CommandMeta(type):
    def __new__(mcs, name, bases, attributes):
        new_attributes = dict(**attributes)
        commands = []

        for k, v in itertools.chain(*(
                z.items() for z in [y.__dict__ for y in bases] + [attributes]
        )):
            if isinstance(v, WrappedCommand):
                commands.append(k)
            if isinstance(v, CommandClass):
                # The ast get to nested's first so this can work.
                commands += v._commands

        new_attributes['_commands'] = commands

        return type.__new__(mcs, name, bases, new_attributes)


class Cli:
    """argparse cli wrapper."""
    def __init__(self, *commands,
                 prog='',
                 description='',
                 formatter_class=CombinedFormatter,
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

        self._global_arguments = global_arguments or []
        self.globals = {}
        self._on_parse = on_parse

        for g in self._global_arguments:
            g.register(self.parser)

        self.commands = {}

        subparsers = self.parser.add_subparsers(
            title='Commands', dest='command'
        )

        for command_name, command, wrapper in commands:
            command.register(subparsers)
            self.commands[command_name] = wrapper

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

        for g in self._global_arguments:
            key = _flags_key(g.flags)
            self.globals[key] = kw.pop(key)

        if callable(self._on_parse):
            self._on_parse(namespace)

        if command:
            await command(**kw)
        elif self.default_command:
            await self.default_command(**vars(namespace))
        else:  # pragma: no cover
            self.parser.print_help()


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

    def __init__(
            self,
            config_file: typing.Union[str, typing.List[str]] = None,
            loop=None,
            executor=None,
            add_dump_config_command=False,
            help_formatter=CombinedFormatter,
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

        self.logger = setup_logger(self.prog_name)
        self.executor = AsyncExecutor(loop, executor)
        self.loop = self.executor.loop

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

        if self.config_class:
            # pylint: disable=not-callable
            self.config: Config = self.config_class()
        elif self.default_configs:
            cls = config_factory(self.default_configs)
            self.config = cls()
        else:
            self.config = Config()

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
            description=str(self.__doc__),
            global_arguments=common_g_arguments + self.global_arguments,
            on_parse=self._on_parse,
            default_command=self.main,
            formatter_class=help_formatter,
        )

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
        self.loop.run_until_complete(self.cli.run(args=args))

    # pylint: disable=unused-argument
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

        if self._config_file:
            if args.config_file:
                self._user_configs = args.config_file

            if self.config_path:
                self.logger.info(f'Using config {self.config_path}')
                self.config.read_file(self.config_path)

        self.logger.info(f'{self.prog_name} {self.version}')
