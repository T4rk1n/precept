import abc
import collections
import inspect
import typing


from .errors import ImmutableError

__all__ = [
    'ImmutableProp',
    'ImmutableDict',
    'ImmutableMeta'
]


class ImmutableProp:
    def __set_name__(self, owner, name):
        self.name = name  # pylint: disable=attribute-defined-outside-init

    def __get__(self, instance, owner):
        # noinspection PyProtectedMember
        return instance._data.get(self.name)


class ImmutableMeta(abc.ABCMeta):
    # pylint: disable=arguments-differ
    def __new__(mcs, name, bases, attributes):
        new_attributes = attributes.copy()

        init = attributes.get('__init__', bases[-1].__init__)
        signature = inspect.signature(init)

        arguments = []

        # Add a ImmutableProp for every init parameters.
        for k in signature.parameters.keys():
            if k not in ('self', 'args', 'kwargs'):
                arguments.append(k)
                new_attributes[k] = ImmutableProp()

        new_attributes['_prop_keys'] = arguments

        return super().__new__(mcs, name, bases, new_attributes)


class ImmutableDict(collections.abc.Mapping, metaclass=ImmutableMeta):
    def __init__(self, **kwargs):
        self._initialized = False
        self._class_attrs = dir(self.__class__)
        self._data = kwargs
        self._initialized = True

    def __getitem__(self, k: str, default=None) -> typing.Any:
        return self._data.get(k, default)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> typing.Iterator[str]:
        for k in self._data:
            yield k

    def __str__(self):  # pragma: no cover
        return str(dict(self))

    def __repr__(self):   # pragma: no cover
        return str(self)

    def __getattribute__(self, item):
        if item.startswith('_') or item in self._class_attrs:
            return super(ImmutableDict, self).__getattribute__(item)

        if item in self._data:
            return self._data[item]

        raise KeyError(f'Invalid key {item}')

    def __setattr__(self, key, value):
        if self.__dict__.get('_initialized'):
            raise ImmutableError(
                f'Property {self.__class__.__name__}.{key} is immutable'
            )
        super(ImmutableDict, self).__setattr__(key, value)
