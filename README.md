# precept

[![CircleCI](https://circleci.com/gh/T4rk1n/precept.svg?style=svg)](https://circleci.com/gh/T4rk1n/precept)
[![Documentation Status](https://readthedocs.org/projects/precept/badge/?version=latest)](https://precept.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/T4rk1n/precept/badge.svg)](https://coveralls.io/github/T4rk1n/precept)
[![PyPI version](https://badge.fury.io/py/precept.svg)](https://badge.fury.io/py/precept)
[![LICENSE](https://img.shields.io/github/license/T4rk1n/precept.svg)](./LICENSE)
[![Downloads](https://pepy.tech/badge/precept)](https://pepy.tech/project/precept)

Async application framework.

## Install

Install with pip: `$ pip install precept`

## Usage

Basic:
```python
from precept import Precept, Command, Argument

class MyCli(Precept):
    """
    The name of the application will be the spinal-case version of 
    the name of the class.
    
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

For local testing:

- Set `entry_points.console_script` to `my-cli = my_package.my_cli:cli` in `setup.py`
- Install locally: `$ pip install -e .`
- Then call: `$ my-cli my-command hello` -> print `hello`

**[Full documentation](http://precept.readthedocs.io/)**
