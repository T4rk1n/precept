import asyncio

from precept import Service, Precept, Command, Argument
from precept.events import EventDispatcher


class Dummy(Service):
    def __init__(self, events):
        super().__init__(events)
        self.results = []
        self.queue = asyncio.Queue()
        self._stop_event = asyncio.Event()
        self._handler = None

    async def setup(self, application):
        self.results = application.results
        self.events.subscribe('send', self.on_send)

    async def start(self):
        self._handler = asyncio.get_event_loop().create_task(self.handler())

    async def handler(self):
        while not self._stop_event.is_set():
            message, go_on = await self.queue.get()
            if go_on:
                self.results.append(message)

    async def stop(self):
        self._stop_event.set()
        self.queue.put_nowait((None, False))
        await self._handler

    async def on_send(self, event):
        await self.queue.put((event.payload.data, True))


class App(Precept):
    def __init__(self):
        super().__init__()
        self.results = []
        self.events.subscribe('dummy_start', self.on_dummy_event)
        self.events.subscribe('dummy_stop', self.on_dummy_event)
        self.events.subscribe('dummy_setup', self.on_dummy_event)
        self.services.append(Dummy(self.events))

    async def on_dummy_event(self, event):
        self.results.append(event.name)

    @Command(Argument('bar'),)
    async def foo(self, bar):
        await self.events.dispatch('send', data=bar)
        await asyncio.sleep(1)


def test_service():
    cli = App()

    cli.start('foo bar'.split())

    assert len(cli.results) == 4
    assert cli.results[0] == 'dummy_setup'
    assert cli.results[1] == 'dummy_start'
    assert cli.results[2] == 'bar'
    assert cli.results[3] == 'dummy_stop'


def test_command_service():
    events = EventDispatcher()

    dummy = Dummy(events)

    class Cli(Precept):
        results = dummy.results

        @Command(services=[dummy])
        async def foo(self):
            await events.dispatch('send', data='foo')
            await asyncio.sleep(1)

    cli = Cli()
    cli.start('foo'.split())

    assert len(dummy.results) == 1
    assert dummy.results[0] == 'foo'
