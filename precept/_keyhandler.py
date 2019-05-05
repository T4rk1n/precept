import asyncio
import sys
import threading

from ._tools import is_windows


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


class KeyHandler:
    def __init__(self, handlers, loop=None):  # pragma: no cover
        self.handlers = handlers
        self.default_handler = self.handlers.get('*')
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
                if not handler:
                    handler = self.default_handler
                if handler:
                    handler(msg, self.stop)
                else:
                    print('no handler')

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
            print(f'{k}: {doc}', file=file)


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
            print(f'echo {msg}', file=sys.stderr)

        async with KeyHandler({'*': hand}, loop=main_loop) as k:
            print('Type 10 chars')
            while not k.stop_event.is_set():
                print('.', end='', flush=True)
                await asyncio.sleep(1, loop=main_loop)

    main_loop.run_until_complete(main())
