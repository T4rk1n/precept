# Changelog

Versions follows [semver](https://semver.org/).

:warning: Expect breaking changes between minor versions prior to `1.0.0` while the api stabilize. 

## [0.5.0]
### Changed

- :hammer: Allow configs to be set on the instance.
- :hammer: Add `print_version` option.

### Added

- :sparkles: Add services to run alongside applications and commands.
- :sparkles: Add plugin system.

## [0.4.0]
### Changed

- :construction: Executor default to ThreadPoolExecutor.
- :construction: Export AsyncExecutor.

### Added

- :sparkles: Add Executor wraps
- :construction: Add Executor max workers argument
- :sparkles: Add Event & Dispatcher
- :sparkles: Add cli events.

## [0.3.1]
### Fixed

- :bug: Fix multiple logging handlers registered during tests.
- :construction: Add options for configuring the logger.

## [0.3.0]
### Changed

- :feet: Moved console related functions to console package.
- :feet: Moved keyhandler to console package.

### Added

- :sparkles: `console.progress_bar`
- :sparkles: Add auto arguments from command functions.
- :sparkles: Add auto global argument for config.
- :construction: Add `symbols` argument to `console.spinner`

### Fixed

- :bug: Config get_root return self if root.

## [0.2.1]
### Fixed

- :hammer: Allow config instance to be set directly.
- :hammer: Add root config class docstring as the first config comment.

## [0.2.0]
### Changed

- :boom: Rename `CliApp` -> `Precept`.
- :hocho: Removed old ConfigProp.
- :hocho: Removed `Precept.configs`, now `Precept.config` with new config api.

### Added

- :sparkles: Command help from docstring.
- :construction: Add help formatter argument.
- :sparkles: Nested commands support, wrap a class into a `Command`.
- :sparkles: Config class
  - Comment support
  - Ini/yaml/json format choices
  - value from environ
  - nestable config attribute lookup
  - config factory.
- :construction: Errors classes: `PreceptError`, `ConfigError`, `ImmutableError`
  
## [0.1.1]
### Fixed

- KeyHandler fixes:
    - Remove no handler print.
    - Add Keys class with most specials keys.
    - Handle ctrl-c by default.
- Fix single argument casing (auto convert to snake_case).

## [0.1.0]
### Added
- Added global `--log-file` option
- Added `execute_with_lock` to `AsyncExecutor` (`CliApp.executor`)
- Added `add_dump_config_command`, adds `prog dump-config outfile` command to output the currently used config file.
- Added `ImmutableDict`, immutable mapping with auto attribute lookup from `__init__` arguments.
- Added `goto_xy`, `getch`.
- Added `KeyHandler`, reads each sys.stdin keys as they come and apply a function according to the key.

### Changed
- Default `main` command on `CliApp` now async.
- Removed `_` prefix from `prog_name`, `global_arguments`, `default_configs`, `version`.
- `Argument` and `configs` are now `ImmutableDict`.
- Removed `kwargs` from `Argument`, all `parser.add_argument` parameters now available as key argument.
- `config_file` can be a list of paths to check for existence in order.

## [0.0.2]
### Fixed
- Added `help` to `Command`
- Set `spinner` default background to `None`

## [0.0.1]
- Initial release
