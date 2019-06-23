# precept

[![CircleCI](https://circleci.com/gh/T4rk1n/precept.svg?style=svg)](https://circleci.com/gh/T4rk1n/precept)
[![Coverage Status](https://coveralls.io/repos/github/T4rk1n/precept/badge.svg)](https://coveralls.io/github/T4rk1n/precept)
[![PyPI version](https://badge.fury.io/py/precept.svg)](https://badge.fury.io/py/precept)
[![LICENSE](https://img.shields.io/github/license/T4rk1n/precept.svg)](./LICENSE)
[![Downloads](https://pepy.tech/badge/precept)](https://pepy.tech/project/precept)

Toolbox to create async command line applications.

## Install 

Install with pip: `$ pip install precept`

## Usage

Basic:
```python
from precept import Precept, Command, Argument

class MyCli(Precept):
    """
    The name of the command will be the name of the class.
    Class docstring is added as cli description.
    """
    @Command(Argument('argument', type=str))
    async def my_command(self, argument):
        print(argument)

def cli():
    MyCli().start()

if __name__ == '__main__':
   cli()
```

For local testing: Set `entry_points.console_script` to `my-cli = my_package.my_cli:cli` in `setup.py` and `$ pip install -e .`

Then call: `$ my-cli my-command hello` -> print `hello`

## License

[MIT license](./LICENSE)

