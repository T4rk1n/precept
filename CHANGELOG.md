# Changelog

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
