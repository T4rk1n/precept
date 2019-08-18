import functools
import stringcase

from .events import EventDispatcher


def _dispatch_wrap(func, event, running):

    @functools.wraps(func)
    async def dispatcher(self, *args, **kwargs):
        self.running = running
        payload = await func(self, *args, **kwargs)
        await self.events.dispatch(event, instance=self)
        return payload

    return dispatcher


class ServiceMeta(type):
    def __new__(mcs, name, bases, attributes):
        _new = dict(**attributes)
        _name = attributes.get('name') or stringcase.snakecase(name)
        _new['name'] = _name

        for _method, _running in (
                ('setup', False), ('start', True), ('stop', False)
        ):
            _func = attributes.get(_method)
            if _func:
                _new[_method] = _dispatch_wrap(
                    _func, f'{_name}_{_method}', _running
                )

        return type.__new__(mcs, name, bases, _new)


class Service(metaclass=ServiceMeta):
    """
    Service's runs alongside the main application.

    Communicate via events.

    :Events:
        - ``{name}_setup`` when added to services.
        - ``{name}_start`` after calling start.
        - ``{name}_stop`` after calling stop.

    """
    name: str = None

    def __init__(self, events: EventDispatcher = None):
        self.events = events or EventDispatcher()
        self.running: bool = False
        self.ready: bool = False

    async def setup(self, application):  # pragma: no cover
        """
        Called when added to services.

        Use this to set events and other post initialization that may need
        the application instance.

        :param application: Precept application
        :type application: precept.Precept
        :return:
        """
        raise NotImplementedError

    async def start(self):  # pragma: no cover
        """
        Start the service.

        :return:
        """
        raise NotImplementedError

    async def stop(self):  # pragma: no cover
        """
        Stop the service.

        :return:
        """
        raise NotImplementedError
