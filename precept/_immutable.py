import abc
import collections
import inspect
import typing


__all__ = [
    'ImmutableProp',
    'ImmutableDict',
    'ImmutableMeta'
]


class ImmutableProp:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        # noinspection PyProtectedMember
        return instance._data.get(self.name)

    def __set__(self, instance, value):
        raise TypeError(
            f'{instance.__class__.__name__}.{self.name} is immutable'
        )


class ImmutableMeta(abc.ABCMeta):
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
        self._data = kwargs

    def __getitem__(self, k: str, default=None) -> typing.Any:
        return self._data.get(k, default)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> typing.Iterator[str]:
        for k in self._data:
            yield k

    def __str__(self):
        return str(dict(self))

    def __repr__(self):
        return str(self)
