class PreceptError(Exception):
    """Base exception thrown by precept"""


class ConfigError(PreceptError):
    """Error in the config system."""


class ImmutableError(PreceptError):
    """Immutable properties cannot change"""
