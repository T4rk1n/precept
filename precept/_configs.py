import collections
import abc
import itertools
import json
import os
import typing
import configparser
from enum import auto

import stringcase
from ruamel import yaml
from ruamel.yaml.comments import CommentedMap

from ._tools import AutoNameEnum
from .errors import ConfigError


undefined = object()


def get_deep(data, *keys, default=None):
    value = data
    found = False
    keys = iter(keys)

    while not found:
        try:
            key = next(keys)
            value = value.get(key, undefined)
            if value is undefined:  # pragma: no cover
                return default, False
        except StopIteration:
            return value, True

    return value, found  # pragma: no cover


def _to_yaml(root: CommentedMap, obj):
    if isinstance(obj, Nestable):
        data = CommentedMap()
        for i, prop in enumerate(
                getattr(type(obj), x) for x in getattr(obj, '_props', [])
        ):
            root.insert(
                i, prop.name, _to_yaml(data, getattr(obj, prop.name)),
                comment=prop.comment
            )
        return root
    return obj


def _to_dict(obj):
    if isinstance(obj, Nestable):
        data = {}
        for k, v in obj.items():
            data[k] = _to_dict(v)
        return data
    return obj


class BaseConfigSerializer:

    def dump(self, configs, path):  # pragma: no cover
        raise NotImplementedError

    def load(self, path):  # pragma: no cover
        raise NotImplementedError


class YamlConfigSerializer(BaseConfigSerializer):
    def dump(self, configs, path):
        ya_data: CommentedMap = CommentedMap()
        root_comment = getattr(configs, '__doc__', None)
        if root_comment:
            ya_data.yaml_set_start_comment(root_comment)

        ya_data = _to_yaml(ya_data, configs)

        with open(path, 'w') as f:
            yaml.dump(ya_data, f, Dumper=yaml.RoundTripDumper)

    def load(self, path):
        with open(path, 'r') as f:
            return yaml.load(f, Loader=yaml.RoundTripLoader)


class JsonConfigSerializer(BaseConfigSerializer):
    def dump(self, configs, path):
        with open(path, 'w') as f:
            json.dump(_to_dict(configs), f)

    def load(self, path):  # pragma: no cover
        with open(path, 'r') as f:
            return json.load(f)


class IniConfigSerializer(BaseConfigSerializer):
    def __init__(self, root_name):
        self.root_name = root_name

    def dump(self, configs, path):
        cfg = configparser.ConfigParser(allow_no_value=True)
        leftovers = []

        root_comment = getattr(configs, '__doc__', '')
        if root_comment:
            cfg.setdefault(self.root_name, {})
            for comment in root_comment.split(os.linesep):
                cfg.set(self.root_name, f'# {comment}', None)

        for p, value, prop in configs.get_prop_paths():
            if '.' in p:
                top = '.'.join(p.split('.')[:-1])
            else:
                top = self.root_name

            cfg.setdefault(top, {})

            if isinstance(value, Nestable):
                # Put it before the first value
                if prop.comment:
                    leftovers = prop.comment.split(os.linesep)
                continue

            if prop.comment:
                for c in itertools.chain(*[
                        leftovers, prop.comment.split(os.linesep)
                ]):
                    cfg.set(top, f'# {c}', None)
                leftovers = []

            if isinstance(value, list):
                cfg[top][prop.name] = yaml.round_trip_dump(value)
            else:
                cfg[top][prop.name] = str(value)

        with open(path, 'w') as f:
            cfg.write(f)

    def load(self, path):
        cfg = configparser.ConfigParser()
        with open(path) as f:
            cfg.read_file(f)

        # noinspection PyProtectedMember
        raw = dict(cfg._sections)
        data = raw.pop(self.root_name)
        for k, v in raw.items():
            # The rest are Nestables.
            sections = k.split('.')
            key = sections[-1]
            last_section = data
            for section in sections[:-1]:
                last_section = last_section.setdefault(section, {})

            last_section[key] = v

        return data


class ConfigFormat(AutoNameEnum):
    YML = auto()
    JSON = auto()
    INI = auto()

    def serializer(self, config):
        if self == ConfigFormat.YML:
            return YamlConfigSerializer()
        if self == ConfigFormat.JSON:
            return JsonConfigSerializer()
        if self == ConfigFormat.INI:
            return IniConfigSerializer(config.root_name)
        raise ConfigError('Invalid config format')  # pragma: no cover


class ConfigProperty:
    def __init__(
            self,
            default=None,
            comment=None,
            config_type=None,
            environ_name=None,
            auto_environ=True,
            name=None,
            auto_global=False,
    ):
        self.default = default
        self.comment = comment
        self.name = name
        self.qualified_name = None
        self.config_type = config_type or type(default) if default else None
        self.environ_name = environ_name
        self.auto_environ = auto_environ
        self.auto_global = auto_global

    def __set_name__(self, owner, name):
        self.name = name
        if not issubclass(owner, Config):
            self.qualified_name = f'{owner.__name__.lower()}.{name}'
        else:
            self.qualified_name = name

        if self.environ_name is None and self.auto_environ:
            self.environ_name = name.upper()

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = undefined

        app = getattr(instance, '_app', None)

        if self.auto_global and app is not None:
            value = app.cli.globals.get(self.qualified_name, undefined)

        if self.environ_name and value is undefined:
            # pylint: disable=invalid-envvar-default
            value = os.getenv(self.environ_name, undefined)

        if value is undefined:
            if issubclass(owner, Config):
                value = instance.get(self.name, self.default)
            else:
                root, levels = instance.get_root(self.name)
                value, found = get_deep(root, *levels)
                if not found:  # pragma: no cover
                    value = self.default

        if value is not None and self.config_type is not None:
            try:
                if isinstance(value, str) and self.config_type == list:
                    value = yaml.round_trip_load(value)
                else:
                    value = self.config_type(value)
            except TypeError as err:
                raise ConfigError(
                    f'Expected type {self.config_type.__name__} for {value}'
                ) from err

        return value

    def __repr__(self):
        return f'<ConfigProperty {self.name}>'


class ConfigMeta(abc.ABCMeta):
    # pylint: disable=arguments-differ
    def __new__(mcs, name, bases, attributes):
        _new = attributes.copy()
        _props = list(itertools.chain(*(
            getattr(b, '_props', []) for b in bases
        )))
        _children = list(itertools.chain(*(
            getattr(b, '_children', []) for b in bases
        )))

        for k, v in attributes.items():
            if isinstance(v, ConfigProperty):
                _props.append(k)
            elif isinstance(v, type) and hasattr(v, '_props'):
                # No way to check if actually a Nestable (chicken or egg?)
                # Adding a Nested class as subclass would mean to have
                # to loop over the attributes of the class and do it
                # recursively. So it needs to be a Nestable otherwise
                # the descriptor will trow because no get_root.
                _key = stringcase.snakecase(k)
                setattr(v, '_key', _key)
                _new[_key] = _NestableDescriptor(
                    f'_{_key}', getattr(v, '_props'), v, comment=v.__doc__
                )
                _children.append(v)
                _props.append(_key)

        _new['_children'] = _children
        _new['_props'] = _props

        # pylint: disable=too-many-function-args
        return abc.ABCMeta.__new__(mcs, name, bases, _new)


class Nestable(collections.abc.Mapping, metaclass=ConfigMeta):
    _parent: typing.Any
    _key: str
    _children = []
    _props = []

    def __init__(self, parent=None, parent_len=0):
        self._parent = parent
        self._parent_len = parent_len
        for child_cls in self._children:
            # noinspection PyProtectedMember
            var_name = child_cls._key
            setattr(
                self,
                var_name,
                child_cls(self, parent_len + 1)
            )

    def get_root(self, current=None):
        parent = self._parent
        if parent is None:
            return self
        levels = [current, self._key] if current else [self._key]
        last_parent = parent
        while parent is not None:
            key = getattr(parent, '_key', None)
            if key is not None:
                levels.append(key)
            last_parent = parent
            parent = getattr(parent, '_parent', None)
        return last_parent, reversed(levels)

    def __getitem__(self, k):
        # Just go into descriptor.
        return getattr(self, k)

    def __len__(self):  # pragma: no cover
        return len(self._props)

    def __iter__(self):
        for prop in self._props:
            yield prop

    def get_prop_paths(self, parent=''):
        children = [getattr(x, '_key') for x in self._children]
        if not parent and hasattr(self, '_key'):  # pragma: no cover
            parent = self._key
        for prop in (getattr(type(self), x) for x in self._props):
            value = getattr(self, prop.name)
            path = f'{parent + "." if parent else ""}{prop.name}'
            yield path, value, prop
            if prop.name in children:
                for k, v, p in value.get_prop_paths(path):
                    yield k, v, p


class _NestableDescriptor(ConfigProperty):

    def __init__(self, nestable, props, nested_cls, comment=None):
        default = {
            prop.name: prop.default
            for prop in (getattr(nested_cls, p) for p in props)
        }
        super().__init__(default, comment, config_type=dict)
        self.nestable = nestable
        self.name = nestable[1:]

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.nestable, self.default)


class Config(Nestable):
    """
    Root config class, assign ConfigProperties as class members.
    """

    def __init__(
            self,
            config_format: ConfigFormat = ConfigFormat.YML,
            root_name='CONFIG'
    ):
        super().__init__(None)
        self._data = {}
        self.config_format = config_format
        self.root_name = root_name
        self._app = None
        self._serializer: BaseConfigSerializer = config_format.serializer(self)

    def __getitem__(self, k):
        # Here get the prop descriptor and return the value or default
        prop = getattr(type(self), k)
        return self._data.get(k, prop.default)

    def read_dict(self, data: dict):
        self._data = data

    def read_file(self, path: str):
        self._data = self._serializer.load(path)

    def save(self, path: str):
        self._serializer.dump(self, path)


def config_factory(data, root=None, key=None):

    props = []
    children = []

    class _Current:
        pass

    for k, v in data.items():
        if isinstance(v, dict):
            nestable = config_factory(v, _Current, k)
            setattr(
                _Current, k,
                _NestableDescriptor(f'_{k}', list(v.keys()), nestable)
            )
            children.append(nestable)
        else:
            setattr(_Current, k, ConfigProperty(name=k, default=v))
        props.append(k)

    setattr(_Current, '_props', props)
    setattr(_Current, '_children', children)

    if root is None:
        class _Wrapped(_Current, Config):
            pass
    else:
        setattr(_Current, '_key', key)

        class _Wrapped(_Current, Nestable):
            pass

    return _Wrapped
