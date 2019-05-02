import asyncio
import sys
import threading

from ._tools import is_windows


class GetChar:
    def __init__(self):
        if is_windows():
            import msvcrt
            self.get_char = msvcrt.getwch
        else:
            import termios
            import tty

            def get_char():
                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)

                try:
                    tty.setraw(fd)
                    raw = termios.tcgetattr(fd)
                    raw[1] = old[1]
                    termios.tcsetattr(fd, termios.TCSADRAIN, raw)
                    ch = sys.stdin.read(1)
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
                return ch

            self.get_char = get_char

    def __call__(self):
        return self.get_char()

    async def deferred(self, executor):
        return await executor.execute(self.get_char)


getch = GetChar()


class KeyHandler:
    def __init__(self, handlers, loop=None):
        self.handlers = handlers
        self.default_handler = self.handlers.get('*')
        self.loop = loop or asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=self.loop)
        self.stop_event = asyncio.Event(loop=self.loop)
        self._consumer = None
        self._producer = None

    def stop(self):
        self.stop_event.set()

    def read(self):
        # Make non-blocking.
        while not self.stop_event.is_set():
            ch = getch()
            asyncio.ensure_future(self.queue.put(ch), loop=self.loop)

    async def handle(self):
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

    async def __aenter__(self):
        self._producer = threading.Thread(target=self.read)
        self._producer.daemon = True
        self._producer.start()
        self._consumer = asyncio.ensure_future(self.handle(), loop=self.loop)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        await self._consumer

    def print_keys(self, file=sys.stdout):
        for k, v in self.handlers.items():
            doc = getattr(v, '__doc__', getattr(v, '__name__', ''))
            print(f'{k}: {doc}', file=file)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    async def main():

        ns = {
            'i': 0
        }

        def hand(msg, stop):
            ns['i'] += 1
            if ns['i'] >= 10:
                stop()
            print(f'echo {msg}', file=sys.stderr)

        async with KeyHandler({'*': hand}, loop=loop) as k:
            print('Type 10 chars')
            while not k.stop_event.is_set():
                print('.', end='', flush=True)
                await asyncio.sleep(1, loop=loop)

    loop.run_until_complete(main())
