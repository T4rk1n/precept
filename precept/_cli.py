"""Class based cli builder with sub commands."""
import argparse
import asyncio
import itertools
import typing
import functools
import inspect

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import stringcase

from ._immutable import ImmutableDict
from ._tools import is_windows


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
                 name=None, description=None, help=None, auto=False):
        self.arguments = arguments
        self._command_name = None
        self.command_name = name
        self.description = description
        self.help = help
        self._wrapped = None
        self.obj_name = None
        self.auto = auto

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
            if self.auto:
                arguments = []
                signature = inspect.signature(obj)
                for k, v in signature.parameters.items():
                    if k in ('self', 'args', 'kwargs'):
                        continue
                    key = stringcase.spinalcase(k)
                    default = None
                    _type = None
                    if v.annotation:
                        _type = v.annotation
                    if v.default is not v.empty:
                        key = f'--{key}'
                        default = v.default
                        if _type is None:
                            _type = type(default)
                    arguments.append(
                        Argument(key, type=_type, default=default)
                    )
                self.arguments = tuple(arguments) + tuple(self.arguments)

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
            title='Commands', dest='command', metavar=''
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
