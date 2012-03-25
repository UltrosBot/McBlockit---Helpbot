# coding=utf-8
"""
    This file contains decorators. They are useful in plugins,
    where some commands may need a user to be a certain rank.
"""

def config(key, value):
    """Decorator that writes to the configuration of the command."""

    def config_inner(func):
        if getattr(func, "config", None) is None:
            func.config = {}
        func.config[key] = value

        return func

    return config_inner