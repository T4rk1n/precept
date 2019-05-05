import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from ruamel import yaml

from precept import CliApp, Command, Argument


override_configs = {
    'config_num': 25,
    'config_str': 'bar',
    'config_list': [5, 4, 5],
    'config_nested': {
        'nested': 'foo',
    }
}

config_files = [
    'config.yml', './tests/configs.yml', './tests/configs2.yml'
]


class ConfigCli(CliApp):
    default_configs = {
        'config_num': 1,
        'config_str': 'foo',
        'config_list': [1, 2, 3],
        'config_nested': {
            'nested': 'bar',
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
        self.result = self.configs.get(config_name)


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
        cli._write_configs(override_configs, config_file)
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
        cli._write_configs(override_configs, config_file)
        cli.start(f'--quiet --config-file {config_file} use-config {config_name}'.split(' '))

        assert cli.result == config_value
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)


def test_dump_config_defaults():
    config_file = './test.yml'
    try:
        cli = ConfigCli()
        cli.start(f'--quiet dump-configs {config_file}'.split(' '))
        assert os.path.exists(config_file)
        with open(config_file, 'r') as f:
            configs = yaml.load(f, Loader=yaml.RoundTripLoader)
        for k, v in CliApp.default_configs.items():
            assert configs[k] == v
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)


def test_dump_config_current_configs():
    config_file = './config.yml'
    output = './output.yml'
    try:
        cli = ConfigCli()
        cli._write_configs(override_configs, config_file)
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
        cli._write_configs(override_configs, config_file)
        for k, v in override_configs.items():
            cli.start(f'--quiet use-config {k}'.split(' '))
            assert cli.result == v
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)
