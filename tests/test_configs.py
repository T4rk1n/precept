import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from ruamel import yaml

from precept import (
    Precept, Command, Argument, Config, ConfigProperty, Nestable, ConfigFormat,
    config_factory)

override_configs = {
    'config_int': 25,
    'config_str': 'bar',
    'config_list': [5, 4, 5],
    'config_nested': {
        'nested_str': 'foo',
    }
}

config_files = [
    'config.yml', './tests/configs.yml', './tests/configs2.yml'
]


class ConfigTest(Config):
    """root_comment"""
    config_str = ConfigProperty(
        comment='comment_string',
        config_type=str,
        auto_environ=True
    )
    config_str_with_default = ConfigProperty(
        default='Default foo bar',
        auto_environ=True,
    )
    config_int = ConfigProperty(default=10, auto_environ=True)
    config_float = ConfigProperty(
        default=89.99,
        comment='comment_float',
        auto_environ=True,
    )
    config_list = ConfigProperty(
        default=[1, 2, 3],
        auto_environ=True,
    )
    config_auto_global = ConfigProperty(
        default=333, auto_global=True, comment='comment_auto_global'
    )

    class ConfigNested(Nestable):
        """docstring_comment"""
        nested_str = ConfigProperty(
            default='nested',
            comment='nested_comment'
        )

        class DoubleNested(Nestable):
            """doubly"""
            double = ConfigProperty(
                default=2.2, comment='double_comment_nested'
            )

        double_nested: DoubleNested = None

    config_nested: ConfigNested = None


override = {
    'config_int': 22,
    'config_str': 'foo',
    'config_float': 55.77,
    'config_str_with_default': 'not default',
    'config_list': [5, 4, 5],
    'config_nested': {
        'nested_str': 'hello',
        'double_nested': {'double': 77.77}
    }
}


class ConfigCli(Precept):
    default_configs = {
        'config_int': 1,
        'config_str': 'foo',
        'config_list': [1, 2, 3],
        'config_nested': {
            'nested_str': 'bar',
        }
    }
    result = None

    def __init__(self):
        super().__init__(
            config_file=config_files,
            executor=ThreadPoolExecutor(),
            add_dump_config_command=True,
        )

    @Command(
        Argument(
            'config_name',
            type=str,
        )
    )
    async def use_config(self, config_name):
        self.result = getattr(self.config, config_name)


@pytest.mark.parametrize(
    'config_name, config_value', list(ConfigCli.default_configs.items())
)
def test_config_defaults(config_name, config_value):
    cli = ConfigCli()
    cli.start(f'--quiet use-config {config_name}'.split(' '))

    assert cli.result == config_value


@pytest.mark.parametrize(
    'config_name, config_value', list(override_configs.items())
)
def test_config_file(config_name, config_value):
    config_file = './config.yml'
    try:
        cli = ConfigCli()
        cli.config.read_dict(override_configs)
        cli.config.save(config_file)

        cli.start(f'--quiet use-config {config_name}'.split(' '))

        assert cli.result == config_value
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)


@pytest.mark.parametrize(
    'config_name, config_value', list(override_configs.items())
)
def test_config_override(config_name, config_value):
    config_file = './custom.yml'
    try:
        cli = ConfigCli()
        cli.config.read_dict(override_configs)
        cli.config.save(config_file)
        cli.start(
            f'--quiet --config-file {config_file}'
            f' use-config {config_name}'.split(' ')
        )

        assert cli.result == config_value
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)


def test_dump_config_defaults():
    config_file = './test.yml'
    try:
        cli = ConfigCli()
        cli.config.config_format = ConfigFormat.YML
        cli.start(f'--quiet dump-configs {config_file}'.split(' '))
        assert os.path.exists(config_file)
        with open(config_file, 'r') as f:
            configs = yaml.load(f, Loader=yaml.RoundTripLoader)
        for k, v in cli.default_configs.items():
            assert configs[k] == v
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)


def test_dump_config_current_configs():
    config_file = './config.yml'
    output = './output.yml'
    try:
        cli = ConfigCli()
        cli.config.config_format = ConfigFormat.YML
        cli.config.read_dict(override_configs)
        cli.config.save(config_file)

        cli.start(f'--quiet dump-configs {output}'.split(' '))
        with open(config_file, 'r') as f:
            configs = yaml.load(f, Loader=yaml.RoundTripLoader)
        for k, v in override_configs.items():
            assert configs[k] == v
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)
        if os.path.exists(output):
            os.remove(output)


@pytest.mark.parametrize(
    'level', list(range(len(config_files)))
)
def test_multi_configs(level):
    config_file = config_files[level]
    try:
        cli = ConfigCli()
        cli.config.read_dict(override_configs)
        cli.config.save(config_file)

        for k, v in override_configs.items():
            cli.start(f'--quiet use-config {k}'.split(' '))
            assert cli.result == v
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)


def test_config_class():
    cfg = ConfigTest()

    # Default values assertions
    assert cfg.config_str_with_default == 'Default foo bar'
    assert cfg.config_nested.nested_str == 'nested'
    assert cfg.config_nested.double_nested.double == 2.2
    assert cfg.config_str is None
    assert cfg.config_list == [1, 2, 3]

    cfg.read_dict(override)

    # Changed values assertions
    assert cfg.config_str == 'foo'
    assert cfg.config_nested.nested_str == 'hello'
    assert cfg['config_nested']['nested_str'] == 'hello'
    # pylint: disable=unsubscriptable-object
    assert cfg.config_nested['nested_str'] == 'hello'
    assert cfg.config_str_with_default == 'not default'
    assert cfg.config_nested.double_nested.double == 77.77


@pytest.mark.parametrize('config_format', [
    ConfigFormat.YML, ConfigFormat.INI, ConfigFormat.TOML
])
def test_config_comments(tmp_path, config_format):
    cfg = ConfigTest(config_format=config_format)

    config_file = os.path.join(tmp_path, 'configs')

    cfg.read_dict(override)

    cfg.save(config_file)

    cfg2 = ConfigTest(config_format=config_format)
    cfg2.read_file(config_file)

    # Test that the comment are not included in the values
    assert cfg2.config_str == 'foo'
    assert cfg2.config_float == 55.77
    assert cfg2.config_nested.nested_str == 'hello'
    assert cfg2.config_nested.double_nested.double == 77.77
    assert cfg2.config_list == [5, 4, 5]

    with open(config_file) as f:
        test = f.read()

    for comment in (
            'comment_string', 'comment_float', 'docstring_comment',
            'nested_comment', 'double_comment_nested', 'doubly', 'root_comment'
    ):
        assert comment in test


def test_config_json(tmp_path):
    cfg = ConfigTest(config_format=ConfigFormat.JSON)
    config_file = os.path.join(tmp_path, 'config.json')

    cfg.save(config_file)

    with open(config_file) as f:
        data = json.load(f)

    assert data['config_nested']['nested_str'] == 'nested'


@pytest.mark.parametrize(
    'name, value', list(
        x for x in override.items() if not isinstance(x[1], dict)
    )
)
def test_config_environ(monkeypatch, name, value):
    monkeypatch.setenv(
        name.upper(),
        str(value)
        if not isinstance(value, list)
        else yaml.round_trip_dump(value)
    )
    cfg = ConfigTest()

    assert getattr(cfg, name) == value


# pylint: disable=no-member
def test_config_factory():
    d = {'flat': 'face', 'nested': {'double': {'keyed': 'alright'}}}
    cls = config_factory(d)
    cfg = cls()

    assert cfg.flat == 'face'
    assert cfg.nested.double.keyed == 'alright'


@pytest.mark.parametrize(
    'config_name, config_value', list(override.items())
)
def test_new_config_cli(config_name, config_value):
    class Cfg(ConfigCli):
        config = ConfigTest()

    cli = Cfg()
    cli.config.read_dict(override)
    cli.start(f'--quiet use-config {config_name}'.split(' '))

    assert cli.result == config_value


def test_config_get_root():
    # Bug used to raise an error, should always return the root.
    c = ConfigTest()
    root = c.get_root()
    assert root is c


def test_config_auto_global():
    class Cfg(ConfigCli):
        config = ConfigTest()
    cli = Cfg()

    cli.start('--config-auto-global=77 use-config config_auto_global'.split())
    assert cli.result == 77


def test_config_set():
    cfg = ConfigTest()
    cfg.config_str = 'Changed'
    assert cfg.config_str == 'Changed'

    cfg.config_nested.nested_str = 'Also changed'
    assert cfg.config_nested.nested_str == 'Also changed'


def test_config_order(tmp_path):
    # Config  order should be
    # - cli arguments
    # - updated dict values
    # - set values
    # - config file.
    cfg = ConfigTest()
    cfg._app = ConfigCli()

    cfg.config_str = 'changed 2'
    cfg.config_nested.nested_str = 'changed one'
    config_path = os.path.join(tmp_path, 'config.toml')

    # Test changed values stays after reading dict.
    cfg.read_dict({'config_str': 'updated'})

    assert cfg.config_nested.nested_str == 'changed one'
    assert cfg.config_str == 'updated'

    # Test that reading the config file doesn't change set values
    cfg2 = ConfigTest()
    cfg2.config_str_with_default = 'Changed again'
    cfg2.config_nested.double_nested.double = 88
    cfg2.save(config_path)

    cfg.read_file(config_path)

    assert cfg.config_str_with_default == 'Changed again'
    assert cfg.config_str == 'updated'
    assert cfg.config_nested.double_nested.double == 88
    assert cfg.config_nested.nested_str == 'changed one'

    # Test argument take precedence over all
    cfg._app.cli.globals = {
        'config_auto_global': 555
    }
    cfg.config_auto_global = 111
    assert cfg.config_auto_global == 555


def test_multi_config_instances():
    cfg1 = ConfigTest()
    cfg2 = ConfigTest()
    cfg1.config_str = 'Foo'

    assert cfg1.config_str != cfg2.config_str

    cfg2.config_nested.nested_str = 'multi-instance'

    assert cfg1.config_nested.nested_str != cfg2.config_nested.nested_str

    cfg1.config_nested.double_nested.double = 3.0

    assert (
        cfg1.config_nested.double_nested.double
        != cfg2.config_nested.double_nested.double
    )


def test_dump_config_str_no_default_no_comment():
    config_file = './config.toml'

    class Conf(Config):
        config_str_no_default_or_comment = ConfigProperty(config_type=str)

    class Cli(Precept):
        config_class = Conf

    cli = Cli(config_file=config_file, add_dump_config_command=True)
    cli.config.config_format = ConfigFormat.TOML

    try:
        cli.start(f'dump-configs {config_file}')
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)


def test_dump_config_str_bool_default_less_40_comment():
    config_file = './config.toml'

    class Conf(Config):
        boolean_cfg = ConfigProperty(
            config_type=bool, default=True, comment='less than 40'
        )

    class Cli(Precept):
        config_class = Conf

    cli = Cli(config_file=config_file, add_dump_config_command=True)
    cli.config.config_format = ConfigFormat.TOML

    try:
        cli.start(f'dump-configs {config_file}')
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)
