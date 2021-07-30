import asyncio
import string
import sys
import threading
from itertools import chain

from precept._tools import is_windows


class Key:  # pragma: no cover
    def __init__(self, value, clean=None):
        self.value = value
        self.clean = clean

    def __str__(self):
        return self.clean or self.value

    def __eq__(self, other):
        if isinstance(other, Key):
            return other.value == self.value
        if isinstance(other, str):
            return other == self.value
        return False

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"<Key '{self.clean or self.value}'>"


class Keys:  # pragma: no cover
    SPACE = Key(' ', 'space')
    BACKSPACE = Key('\x7f', 'backspace')
    ENTER = Key('\r', 'enter')
    ESCAPE = Key('\x1b', 'escape')
    INSERT = Key('\x1b[2~', 'insert')
    END = Key('\x1b[F', 'end')
    HOME = Key('\x1b[H', 'home')
    DELETE = Key('\x1b[3~', 'delete')
    DOWN = Key('\x1b[B', 'down')
    UP = Key('\x1b[A', 'up')
    LEFT = Key('\x1b[D', 'left')
    RIGHT = Key('\x1b[C', 'right')

    F1 = Key('\x1bOP', 'F1')
    F2 = Key('\x1bOQ', 'F2')
    F3 = Key('\x1bOR', 'F3')
    F4 = Key('\x1bOS', 'F4')
    F5 = Key('\x1bO15~', 'F5')
    F6 = Key('\x1bO17~', 'F6')
    F7 = Key('\x1bO18~', 'F7')
    F8 = Key('\x1bO19~', 'F8')
    F9 = Key('\x1bO20~', 'F9')
    F10 = Key('\x1bO21~', 'F10')
    F11 = Key('\x1bO23~', 'F11')
    F12 = Key('\x1bO24~', 'F12')

    CTRL_C = Key('\x03', 'ctrl-c')
    CTRL_A = Key('\x01', 'ctrl-a')
    CTRL_ALT_A = Key('\x1b\x01', 'ctrl-alt-a')
    CTRL_ALT_DEL = Key('\x1b[3^', 'ctrl-alt-del')
    CTRL_B = Key('\x02', 'ctrl-b')
    CTRL_D = Key('\x04', 'ctrl-d')
    CTRL_E = Key('\x05', 'ctrl-e')
    CTRL_F = Key('\x06', 'ctrl-f')
    CTRL_Z = Key('\x1a', 'ctrl-z')

    SPECIAL_KEYS = (
        SPACE, BACKSPACE, ENTER, ESCAPE, INSERT, END, HOME,
        DELETE, DOWN, UP, LEFT, RIGHT,
        F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12,
        CTRL_C, CTRL_A, CTRL_ALT_A, CTRL_ALT_DEL, CTRL_B,
        CTRL_D, CTRL_E, CTRL_F, CTRL_Z
    )
    keys = {
        x: Key(x) for x in chain(string.ascii_letters, string.digits)
    }
    keys.update({
        x.value: x for x in SPECIAL_KEYS
    })

    @classmethod
    def get_key(cls, value, default=None):
        return cls.keys.get(value) or default


class GetChar:
    def __init__(self):  # pragma: no cover
        if is_windows():
            # pylint: disable=import-error
            import msvcrt
            self.get_char = msvcrt.getwch
        else:
            import termios
            import tty

            def get_char():
                # pylint: disable=assignment-from-no-return
                fileno = sys.stdin.fileno()
                old = termios.tcgetattr(fileno)

                try:
                    tty.setraw(fileno)
                    raw = termios.tcgetattr(fileno)
                    raw[1] = old[1]
                    termios.tcsetattr(fileno, termios.TCSADRAIN, raw)
                    char = sys.stdin.read(1)
                finally:
                    termios.tcsetattr(fileno, termios.TCSADRAIN, old)
                return char

            self.get_char = get_char

    def __call__(self):  # pragma: no cover
        return self.get_char()

    async def deferred(self, executor):  # pragma: no cover
        return await executor.execute(self.get_char)


getch = GetChar()


class KeyHandler:  # pragma: no cover
    def __init__(self, handlers, loop=None, default_handler=None):  # pragma: no cover # noqa: E501
        self.handlers = handlers
        self.handlers.update({
            Keys.CTRL_C: lambda _, stop: stop(),
        })
        self.default_handler = default_handler
        self.loop = loop or asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=self.loop)
        self.stop_event = asyncio.Event(loop=self.loop)
        self._consumer = None
        self._producer = None

    def stop(self):  # pragma: no cover
        self.stop_event.set()

    def read(self):  # pragma: no cover
        # Make non-blocking.
        while not self.stop_event.is_set():
            char = getch()
            asyncio.ensure_future(self.queue.put(char), loop=self.loop)

    async def handle(self):  # pragma: no cover
        while not self.stop_event.is_set():
            await asyncio.sleep(0.00001)
            try:
                msg = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            else:
                handler = self.handlers.get(msg)
                if handler:
                    handler(msg, self.stop)
                elif self.default_handler:
                    self.default_handler(msg, self.stop)

    async def __aenter__(self):  # pragma: no cover
        self._producer = threading.Thread(target=self.read)
        self._producer.daemon = True
        self._producer.start()
        self._consumer = asyncio.ensure_future(self.handle(), loop=self.loop)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # pragma: no cover
        self.stop()
        await self._consumer

    def print_keys(self, file=sys.stdout):  # pragma: no cover
        for k, v in self.handlers.items():
            doc = getattr(v, '__doc__', getattr(v, '__name__', ''))
            clean_key = Keys.get_key(k, k)
            if k == Keys.CTRL_C:
                continue
            print(f'{clean_key}: {doc}', file=file)


if __name__ == '__main__':  # pragma: no cover
    main_loop = asyncio.get_event_loop()

    async def main():

        namespace = {
            'i': 0
        }

        def hand(msg, stop):
            namespace['i'] += 1
            if namespace['i'] >= 10:
                stop()
            print(repr(msg), file=sys.stderr)

        async with KeyHandler({}, default_handler=hand) as k:
            k.print_keys()
            print('Type 10 chars')
            while not k.stop_event.is_set():
                print('.', end='', flush=True)
                await asyncio.sleep(1)

    main_loop.run_until_complete(main())
